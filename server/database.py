import sqlite3
import json
import os
import uuid
import calendar as cal
from datetime import date, timedelta, datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "life_erp.db")
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "database.json")

# Tables that should NOT be synced to clients
NON_SYNC_TABLES = {"task_runs", "task_logs", "_change_log"}

# Callback for broadcasting changes via WebSocket (set by main.py)
_ws_broadcast_fn = None

def set_ws_broadcast(fn):
    global _ws_broadcast_fn
    _ws_broadcast_fn = fn

def load_schema():
    with open(SCHEMA_PATH, "r") as f:
        return json.load(f)

def get_synced_schema():
    """Return only the tables that should be synced to clients."""
    schema = load_schema()
    return {
        name: defn for name, defn in schema.items()
        if name not in NON_SYNC_TABLES and not defn.get("sync") == False
    }

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def sync_schema():
    """Create or update tables to match database.json definitions."""
    schema = load_schema()
    conn = get_connection()

    for table_name, table_def in schema.items():
        columns = table_def["columns"]

        # Check if table exists
        existing = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,)
        ).fetchone()

        if not existing:
            # Create table
            col_defs = []
            pk_cols = []
            for col_name, col_opts in columns.items():
                col_type = col_opts["type"]
                col_defs.append(f"{col_name} {col_type}")
                if col_opts.get("primary_key"):
                    pk_cols.append(col_name)
            if pk_cols:
                col_defs.append(f"PRIMARY KEY ({', '.join(pk_cols)})")
            sql = f"CREATE TABLE {table_name} ({', '.join(col_defs)}) STRICT"
            conn.execute(sql)
        else:
            # Get current columns
            pragma = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
            existing_cols = {row["name"] for row in pragma}
            desired_cols = set(columns.keys())

            # Add missing columns
            for col_name in desired_cols - existing_cols:
                col_type = columns[col_name]["type"]
                conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type}")
                print(f"  Added column {table_name}.{col_name} ({col_type})")

            # Drop removed columns
            for col_name in existing_cols - desired_cols:
                conn.execute(f"ALTER TABLE {table_name} DROP COLUMN {col_name}")
                print(f"  Dropped column {table_name}.{col_name}")

    conn.commit()
    conn.close()

def get_pk_columns(table_name):
    """Return the list of primary key column names for a table."""
    schema = load_schema()
    table_def = schema[table_name]
    return [
        name for name, opts in table_def["columns"].items()
        if opts.get("primary_key")
    ]

def get_valid_columns(table_name):
    """Return the set of non-PK column names for a table from the schema."""
    schema = load_schema()
    table_def = schema[table_name]
    return {
        name for name, opts in table_def["columns"].items()
        if not opts.get("primary_key")
    }

# ── Change Log ──

def log_change(table_name, pk_value, op, data, timestamp=None, client_id="server"):
    """Record a change in _change_log and broadcast via WebSocket.
    pk_value: dict of PK column->value pairs (JSON-encoded for storage).
    op: 'upsert' or 'delete'.
    data: dict of changed fields (for upsert) or None (for delete).
    Returns the seq number assigned.
    """
    if timestamp is None:
        timestamp = datetime.now().isoformat(timespec="milliseconds")
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO _change_log (table_name, pk_value, op, data, timestamp, client_id) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (table_name, json.dumps(pk_value), op, json.dumps(data) if data is not None else None, timestamp, client_id)
    )
    seq = cursor.lastrowid
    conn.commit()
    conn.close()

    change = {
        "seq": seq,
        "table": table_name,
        "pk": pk_value,
        "op": op,
        "data": data,
        "timestamp": timestamp,
        "client_id": client_id,
    }
    if _ws_broadcast_fn:
        _ws_broadcast_fn(change, exclude_client=client_id)
    return seq

def get_changes_since(seq):
    """Return all changes with seq > given value."""
    conn = get_connection()
    cursor = conn.execute(
        "SELECT * FROM _change_log WHERE seq > ? ORDER BY seq ASC",
        (seq,)
    )
    changes = []
    for row in cursor.fetchall():
        changes.append({
            "seq": row["seq"],
            "table": row["table_name"],
            "pk": json.loads(row["pk_value"]),
            "op": row["op"],
            "data": json.loads(row["data"]) if row["data"] else None,
            "timestamp": row["timestamp"],
            "client_id": row["client_id"],
        })
    conn.close()
    return changes

def get_last_seq():
    """Return the current max seq, or 0 if empty."""
    conn = get_connection()
    row = conn.execute("SELECT COALESCE(MAX(seq), 0) as m FROM _change_log").fetchone()
    conn.close()
    return row["m"]

def apply_client_changes(changes, client_id):
    """Apply a batch of changes from a client using field-level LWW.
    Returns list of (change, assigned_seq) for acknowledged changes.
    """
    results = []
    conn = get_connection()
    for ch in changes:
        table = ch["table"]
        pk = ch["pk"]
        op = ch["op"]
        data = ch.get("data")
        timestamp = ch["timestamp"]

        if table in NON_SYNC_TABLES:
            continue

        schema = load_schema()
        if table not in schema:
            continue

        pk_cols = get_pk_columns(table)

        if op == "delete":
            # Build WHERE from pk
            where = " AND ".join(f"{c} = ?" for c in pk_cols)
            pk_vals = [pk[c] for c in pk_cols]
            conn.execute(f"DELETE FROM {table} WHERE {where}", pk_vals)
        elif op == "upsert" and data:
            # Check if row exists
            where = " AND ".join(f"{c} = ?" for c in pk_cols)
            pk_vals = [pk[c] for c in pk_cols]
            existing = conn.execute(f"SELECT * FROM {table} WHERE {where}", pk_vals).fetchone()

            if existing:
                # Field-level LWW: check existing change_log for each field
                # For simplicity with single-user, just apply the update
                set_parts = []
                set_vals = []
                for col, val in data.items():
                    if col not in pk_cols:
                        set_parts.append(f"{col} = ?")
                        set_vals.append(val)
                if set_parts:
                    set_vals.extend(pk_vals)
                    conn.execute(
                        f"UPDATE {table} SET {', '.join(set_parts)} WHERE {where}",
                        set_vals
                    )
            else:
                # Insert: merge pk + data
                all_data = {**pk, **(data or {})}
                cols = list(all_data.keys())
                vals = [all_data[c] for c in cols]
                placeholders = ", ".join("?" for _ in cols)
                conn.execute(
                    f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({placeholders})",
                    vals
                )

        conn.commit()

        # Log the change with server-assigned seq
        cursor = conn.execute(
            "INSERT INTO _change_log (table_name, pk_value, op, data, timestamp, client_id) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (table, json.dumps(pk), op, json.dumps(data) if data else None, timestamp, client_id)
        )
        seq = cursor.lastrowid
        conn.commit()

        change_out = {
            "seq": seq,
            "table": table,
            "pk": pk,
            "op": op,
            "data": data,
            "timestamp": timestamp,
            "client_id": client_id,
        }
        results.append(change_out)

        # Broadcast to other clients
        if _ws_broadcast_fn:
            _ws_broadcast_fn(change_out, exclude_client=client_id)

    conn.close()
    return results

def get_full_table_data(table_name):
    """Return all rows from a table as list of dicts."""
    conn = get_connection()
    cursor = conn.execute(f"SELECT * FROM {table_name}")
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

def get_full_sync_snapshot():
    """Return all data from all synced tables as a list of Change-like dicts.
    Used for initial sync when client has no data (last_seq == 0)."""
    schema = get_synced_schema()
    changes = []
    conn = get_connection()
    for table_name, table_def in schema.items():
        pk_cols = [
            name for name, opts in table_def["columns"].items()
            if opts.get("primary_key")
        ]
        cursor = conn.execute(f"SELECT * FROM {table_name}")
        for row in cursor.fetchall():
            row_dict = dict(row)
            pk = {col: row_dict[col] for col in pk_cols}
            changes.append({
                "table": table_name,
                "pk": pk,
                "op": "upsert",
                "data": row_dict,
                "timestamp": datetime.now().isoformat(),
            })
    conn.close()
    return changes

def ensure_habit_rows():
    """Ensure rows exist from the earliest existing date (or today) up to today + 100 days."""
    conn = get_connection()

    earliest_row = conn.execute("SELECT MIN(date) as d FROM habits").fetchone()
    start = date.fromisoformat(earliest_row["d"]) if earliest_row["d"] else date.today()
    end = date.today() + timedelta(days=100)

    # Batch insert missing dates
    current = start
    while current <= end:
        conn.execute(
            "INSERT INTO habits (date) VALUES (?) ON CONFLICT(date) DO NOTHING",
            (current.isoformat(),)
        )
        current += timedelta(days=1)

    conn.commit()
    conn.close()

def get_all_habits():
    ensure_habit_rows()
    conn = get_connection()
    cursor = conn.execute("SELECT * FROM habits ORDER BY date ASC")
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

def set_habit_value(date_str, column, value):
    valid = get_valid_columns("habits")
    if column not in valid:
        raise ValueError(f"Invalid column: {column}")

    conn = get_connection()
    conn.execute(
        "INSERT INTO habits (date) VALUES (?) ON CONFLICT(date) DO NOTHING",
        (date_str,)
    )
    conn.execute(
        f"UPDATE habits SET {column} = ? WHERE date = ?",
        (value, date_str)
    )
    conn.commit()

    cursor = conn.execute("SELECT * FROM habits WHERE date = ?", (date_str,))
    row = dict(cursor.fetchone())
    conn.close()
    log_change("habits", {"date": date_str}, "upsert", {column: value})
    return row

DEFAULT_SETTINGS = {
    "work_mn": "300",
    "watchlist": "AAPL,MSFT,GOOGL,AMZN,TSLA",
}

# ── Workout Presets ──

def get_workout_presets():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM workout_presets ORDER BY position ASC, id ASC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def create_workout_preset(name, content):
    conn = get_connection()
    preset_id = str(uuid.uuid4())
    max_pos = conn.execute("SELECT COALESCE(MAX(position), 0) FROM workout_presets").fetchone()[0]
    conn.execute(
        "INSERT INTO workout_presets (id, name, content, position) VALUES (?, ?, ?, ?)",
        (preset_id, name, content, max_pos + 1)
    )
    conn.commit()
    row = dict(conn.execute("SELECT * FROM workout_presets WHERE id = ?", (preset_id,)).fetchone())
    conn.close()
    log_change("workout_presets", {"id": preset_id}, "upsert", row)
    return row

def update_workout_preset(preset_id, name, content):
    conn = get_connection()
    conn.execute("UPDATE workout_presets SET name = ?, content = ? WHERE id = ?", (name, content, preset_id))
    conn.commit()
    row = conn.execute("SELECT * FROM workout_presets WHERE id = ?", (preset_id,)).fetchone()
    conn.close()
    if row is None:
        raise ValueError(f"Preset {preset_id} not found")
    result = dict(row)
    log_change("workout_presets", {"id": preset_id}, "upsert", {"name": name, "content": content})
    return result

def delete_workout_preset(preset_id):
    conn = get_connection()
    conn.execute("DELETE FROM workout_presets WHERE id = ?", (preset_id,))
    conn.commit()
    conn.close()
    log_change("workout_presets", {"id": preset_id}, "delete", None)

# ── Habit Timer ──

TIMER_ACTIVITIES = {'job', 'business', 'reading_watching', 'misc', 'girls_family', 'mma'}

def get_habit_timers():
    """Get all active timers."""
    conn = get_connection()
    rows = conn.execute("SELECT * FROM habit_timer ORDER BY id ASC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def start_habit_timer(activity, started_at):
    """Start a new timer. Multiple timers can run concurrently."""
    if activity not in TIMER_ACTIVITIES:
        raise ValueError(f"Invalid activity: {activity}")
    timer_id = str(uuid.uuid4())
    conn = get_connection()
    conn.execute(
        "INSERT INTO habit_timer (id, activity, started_at, paused_at, accumulated_ms) VALUES (?, ?, ?, NULL, 0)",
        (timer_id, activity, started_at)
    )
    conn.commit()
    row = dict(conn.execute("SELECT * FROM habit_timer WHERE id = ?", (timer_id,)).fetchone())
    conn.close()
    log_change("habit_timer", {"id": timer_id}, "upsert", row)
    return row

def pause_habit_timer(timer_id, paused_at):
    """Pause a specific timer."""
    conn = get_connection()
    row = conn.execute("SELECT * FROM habit_timer WHERE id = ?", (timer_id,)).fetchone()
    if row is None:
        conn.close()
        raise ValueError(f"Timer {timer_id} not found")
    if row["paused_at"] is not None:
        conn.close()
        raise ValueError("Timer is already paused")
    conn.execute("UPDATE habit_timer SET paused_at = ? WHERE id = ?", (paused_at, timer_id))
    conn.commit()
    result = dict(conn.execute("SELECT * FROM habit_timer WHERE id = ?", (timer_id,)).fetchone())
    conn.close()
    log_change("habit_timer", {"id": timer_id}, "upsert", {"paused_at": paused_at})
    return result

def resume_habit_timer(timer_id, resumed_at):
    """Resume a paused timer, accumulating the paused duration."""
    conn = get_connection()
    row = conn.execute("SELECT * FROM habit_timer WHERE id = ?", (timer_id,)).fetchone()
    if row is None:
        conn.close()
        raise ValueError(f"Timer {timer_id} not found")
    if row["paused_at"] is None:
        conn.close()
        raise ValueError("Timer is not paused")
    from datetime import datetime
    paused_dt = datetime.fromisoformat(row["paused_at"])
    resumed_dt = datetime.fromisoformat(resumed_at)
    pause_duration_ms = (resumed_dt - paused_dt).total_seconds() * 1000
    new_accumulated = (row["accumulated_ms"] or 0) + pause_duration_ms
    conn.execute(
        "UPDATE habit_timer SET paused_at = NULL, accumulated_ms = ? WHERE id = ?",
        (new_accumulated, timer_id)
    )
    conn.commit()
    result = dict(conn.execute("SELECT * FROM habit_timer WHERE id = ?", (timer_id,)).fetchone())
    conn.close()
    log_change("habit_timer", {"id": timer_id}, "upsert", {"paused_at": None, "accumulated_ms": new_accumulated})
    return result

def stop_habit_timer(timer_id, stopped_at):
    """Stop a specific timer, compute elapsed minutes per day, apply to habits, delete it."""
    conn = get_connection()
    row = conn.execute("SELECT * FROM habit_timer WHERE id = ?", (timer_id,)).fetchone()
    if row is None:
        conn.close()
        raise ValueError(f"Timer {timer_id} not found")

    from datetime import datetime
    activity = row["activity"]
    if activity not in TIMER_ACTIVITIES:
        conn.close()
        raise ValueError(f"Invalid activity in timer: {activity}")
    started_at = datetime.fromisoformat(row["started_at"])
    accumulated_ms = row["accumulated_ms"] or 0

    # If paused, add pause duration to accumulated
    if row["paused_at"] is not None:
        paused_dt = datetime.fromisoformat(row["paused_at"])
        stopped_dt = datetime.fromisoformat(stopped_at)
        accumulated_ms += (stopped_dt - paused_dt).total_seconds() * 1000
        effective_end = paused_dt
    else:
        effective_end = datetime.fromisoformat(stopped_at)

    total_active_ms = (effective_end - started_at).total_seconds() * 1000 - accumulated_ms
    if total_active_ms < 0:
        total_active_ms = 0

    # Split active time across days proportionally
    day_minutes = {}
    day_wall = {}
    ct = started_at
    while ct < effective_end:
        day_str = ct.strftime("%Y-%m-%d")
        next_midnight = datetime.fromisoformat(day_str) + timedelta(days=1)
        day_end = min(next_midnight, effective_end)
        wall_ms = (day_end - ct).total_seconds() * 1000
        day_wall[day_str] = day_wall.get(day_str, 0) + wall_ms
        ct = day_end

    total_wall_ms = sum(day_wall.values())
    if total_wall_ms > 0:
        for day_str, wall_ms in day_wall.items():
            ratio = wall_ms / total_wall_ms
            active_mn = (total_active_ms * ratio) / 60000
            day_minutes[day_str] = int(active_mn)

    # Apply to habits
    for day_str, minutes in day_minutes.items():
        if minutes <= 0:
            continue
        conn.execute(
            "INSERT INTO habits (date) VALUES (?) ON CONFLICT(date) DO NOTHING",
            (day_str,)
        )
        current = conn.execute(
            f"SELECT {activity} FROM habits WHERE date = ?", (day_str,)
        ).fetchone()
        current_val = current[activity] if current and current[activity] is not None else 0
        new_val = current_val + minutes
        conn.execute(
            f"UPDATE habits SET {activity} = ? WHERE date = ?",
            (new_val, day_str)
        )

    conn.execute("DELETE FROM habit_timer WHERE id = ?", (timer_id,))
    conn.commit()
    conn.close()
    # Log habit changes and timer deletion
    for day_str, minutes in day_minutes.items():
        if minutes > 0:
            log_change("habits", {"date": day_str}, "upsert", {activity: minutes})
    log_change("habit_timer", {"id": timer_id}, "delete", None)
    return {"activity": activity, "day_minutes": day_minutes}

def get_all_settings():
    conn = get_connection()
    # Ensure defaults exist
    for key, val in DEFAULT_SETTINGS.items():
        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO NOTHING",
            (key, val)
        )
    conn.commit()
    cursor = conn.execute("SELECT key, value FROM settings")
    result = {row["key"]: row["value"] for row in cursor.fetchall()}
    conn.close()
    return result

def set_setting(key, value):
    conn = get_connection()
    conn.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = ?",
        (key, value, value)
    )
    conn.commit()
    conn.close()
    log_change("settings", {"key": key}, "upsert", {"value": value})

# ── Workouts ──

def ensure_workout_rows():
    """Ensure rows exist from the earliest existing date (or today) up to today + 100 days."""
    conn = get_connection()
    earliest_row = conn.execute("SELECT MIN(date) as d FROM workouts").fetchone()
    start = date.fromisoformat(earliest_row["d"]) if earliest_row["d"] else date.today()
    end = date.today() + timedelta(days=100)
    current = start
    while current <= end:
        conn.execute(
            "INSERT INTO workouts (date) VALUES (?) ON CONFLICT(date) DO NOTHING",
            (current.isoformat(),)
        )
        current += timedelta(days=1)
    conn.commit()
    conn.close()

def get_all_workouts():
    ensure_workout_rows()
    conn = get_connection()
    cursor = conn.execute("SELECT * FROM workouts ORDER BY date ASC")
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

def set_workout_value(date_str, column, value):
    valid = get_valid_columns("workouts")
    if column not in valid:
        raise ValueError(f"Invalid column: {column}")
    conn = get_connection()
    conn.execute(
        "INSERT INTO workouts (date) VALUES (?) ON CONFLICT(date) DO NOTHING",
        (date_str,)
    )
    conn.execute(
        f"UPDATE workouts SET {column} = ? WHERE date = ?",
        (value, date_str)
    )
    conn.commit()
    cursor = conn.execute("SELECT * FROM workouts WHERE date = ?", (date_str,))
    row = dict(cursor.fetchone())
    conn.close()
    log_change("workouts", {"date": date_str}, "upsert", {column: value})
    return row

# ── Chores ──

def get_all_chores():
    conn = get_connection()
    cursor = conn.execute("SELECT * FROM chores ORDER BY id ASC")
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

def create_chore(title, interval_days):
    conn = get_connection()
    chore_id = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO chores (id, title, interval_days) VALUES (?, ?, ?)",
        (chore_id, title, interval_days)
    )
    conn.commit()
    row = dict(conn.execute("SELECT * FROM chores WHERE id = ?", (chore_id,)).fetchone())
    conn.close()
    log_change("chores", {"id": chore_id}, "upsert", row)
    return row

def update_chore(chore_id, title, interval_days):
    conn = get_connection()
    conn.execute(
        "UPDATE chores SET title = ?, interval_days = ? WHERE id = ?",
        (title, interval_days, chore_id)
    )
    conn.commit()
    row = conn.execute("SELECT * FROM chores WHERE id = ?", (chore_id,)).fetchone()
    conn.close()
    if not row:
        raise ValueError(f"Chore {chore_id} not found")
    log_change("chores", {"id": chore_id}, "upsert", {"title": title, "interval_days": interval_days})
    return dict(row)

def delete_chore(chore_id):
    conn = get_connection()
    conn.execute("DELETE FROM chores WHERE id = ?", (chore_id,))
    conn.commit()
    conn.close()
    log_change("chores", {"id": chore_id}, "delete", None)

def mark_chore_done(chore_id, done_date=None):
    if done_date is None:
        done_date = date.today().isoformat()
    conn = get_connection()
    conn.execute(
        "UPDATE chores SET last_done = ? WHERE id = ?",
        (done_date, chore_id)
    )
    conn.commit()
    row = conn.execute("SELECT * FROM chores WHERE id = ?", (chore_id,)).fetchone()
    conn.close()
    if not row:
        raise ValueError(f"Chore {chore_id} not found")
    log_change("chores", {"id": chore_id}, "upsert", {"last_done": done_date})
    return dict(row)

# ── Todos ──

def get_all_todos():
    conn = get_connection()
    cursor = conn.execute("SELECT * FROM todos ORDER BY id DESC")
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

def create_todo(title):
    conn = get_connection()
    todo_id = str(uuid.uuid4())
    now = date.today().isoformat()
    conn.execute(
        "INSERT INTO todos (id, title, status, created_at) VALUES (?, ?, 'open', ?)",
        (todo_id, title, now)
    )
    conn.commit()
    row = dict(conn.execute("SELECT * FROM todos WHERE id = ?", (todo_id,)).fetchone())
    conn.close()
    log_change("todos", {"id": todo_id}, "upsert", row)
    return row

def update_todo(todo_id, title):
    conn = get_connection()
    conn.execute("UPDATE todos SET title = ? WHERE id = ?", (title, todo_id))
    conn.commit()
    row = conn.execute("SELECT * FROM todos WHERE id = ?", (todo_id,)).fetchone()
    conn.close()
    if not row:
        raise ValueError(f"Todo {todo_id} not found")
    log_change("todos", {"id": todo_id}, "upsert", {"title": title})
    return dict(row)

def set_todo_status(todo_id, status):
    conn = get_connection()
    updates = "status = ?"
    params = [status]
    data = {"status": status}
    if status == "closed":
        closed_at = date.today().isoformat()
        updates += ", closed_at = ?"
        params.append(closed_at)
        data["closed_at"] = closed_at
    else:
        updates += ", closed_at = NULL"
        data["closed_at"] = None
    params.append(todo_id)
    conn.execute(f"UPDATE todos SET {updates} WHERE id = ?", params)
    conn.commit()
    row = conn.execute("SELECT * FROM todos WHERE id = ?", (todo_id,)).fetchone()
    conn.close()
    if not row:
        raise ValueError(f"Todo {todo_id} not found")
    log_change("todos", {"id": todo_id}, "upsert", data)
    return dict(row)

def get_todo_messages(todo_id):
    conn = get_connection()
    cursor = conn.execute(
        "SELECT * FROM todo_messages WHERE todo_id = ? ORDER BY id ASC",
        (todo_id,)
    )
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

def create_todo_message(todo_id, content):
    conn = get_connection()
    msg_id = str(uuid.uuid4())
    now = date.today().isoformat()
    conn.execute(
        "INSERT INTO todo_messages (id, todo_id, content, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
        (msg_id, todo_id, content, now, now)
    )
    conn.commit()
    row = dict(conn.execute("SELECT * FROM todo_messages WHERE id = ?", (msg_id,)).fetchone())
    conn.close()
    log_change("todo_messages", {"id": msg_id}, "upsert", row)
    return row

def update_todo_message(message_id, content):
    conn = get_connection()
    now = date.today().isoformat()
    conn.execute(
        "UPDATE todo_messages SET content = ?, updated_at = ? WHERE id = ?",
        (content, now, message_id)
    )
    conn.commit()
    row = conn.execute("SELECT * FROM todo_messages WHERE id = ?", (message_id,)).fetchone()
    conn.close()
    if not row:
        raise ValueError(f"Message {message_id} not found")
    log_change("todo_messages", {"id": message_id}, "upsert", {"content": content, "updated_at": now})
    return dict(row)

def delete_todo_message(message_id):
    conn = get_connection()
    conn.execute("DELETE FROM todo_messages WHERE id = ?", (message_id,))
    conn.commit()
    conn.close()
    log_change("todo_messages", {"id": message_id}, "delete", None)

# ── Calendar Events ──

def get_calendar_events(start_date, end_date):
    conn = get_connection()
    cursor = conn.execute(
        "SELECT * FROM calendar_events WHERE date >= ? AND date <= ? ORDER BY date, time",
        (start_date, end_date)
    )
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

def create_calendar_event(title, evt_date, evt_time=None, category="personal"):
    conn = get_connection()
    evt_id = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO calendar_events (id, title, date, time, category, auto) VALUES (?, ?, ?, ?, ?, 0)",
        (evt_id, title, evt_date, evt_time, category)
    )
    conn.commit()
    row = dict(conn.execute("SELECT * FROM calendar_events WHERE id = ?", (evt_id,)).fetchone())
    conn.close()
    log_change("calendar_events", {"id": evt_id}, "upsert", row)
    return row

def update_calendar_event(evt_id, title, evt_date, evt_time=None, category="personal"):
    conn = get_connection()
    conn.execute(
        "UPDATE calendar_events SET title = ?, date = ?, time = ?, category = ? WHERE id = ? AND auto = 0",
        (title, evt_date, evt_time, category, evt_id)
    )
    conn.commit()
    row = conn.execute("SELECT * FROM calendar_events WHERE id = ?", (evt_id,)).fetchone()
    conn.close()
    if not row:
        raise ValueError(f"Event {evt_id} not found")
    log_change("calendar_events", {"id": evt_id}, "upsert", {"title": title, "date": evt_date, "time": evt_time, "category": category})
    return dict(row)

def delete_calendar_event(evt_id):
    conn = get_connection()
    conn.execute("DELETE FROM calendar_events WHERE id = ? AND auto = 0", (evt_id,))
    conn.commit()
    conn.close()
    log_change("calendar_events", {"id": evt_id}, "delete", None)


def _third_wednesday(year, month):
    """Return the date of the third Wednesday of the given month."""
    # First day of month
    first = date(year, month, 1)
    # weekday(): Monday=0 ... Sunday=6; Wednesday=2
    offset = (2 - first.weekday()) % 7
    first_wed = first + timedelta(days=offset)
    return first_wed + timedelta(weeks=2)


def _third_friday(year, month):
    """Return the date of the third Friday (monthly options expiration)."""
    first = date(year, month, 1)
    offset = (4 - first.weekday()) % 7
    first_fri = first + timedelta(days=offset)
    return first_fri + timedelta(weeks=2)


# FOMC meeting dates (scheduled 8 times/year, these are the announcement dates)
# Source: federalreserve.gov — update annually
FOMC_DATES = {
    2025: ["01-29", "03-19", "05-07", "06-18", "07-30", "09-17", "10-29", "12-17"],
    2026: ["01-28", "03-18", "05-06", "06-17", "07-29", "09-16", "10-28", "12-16"],
    2027: ["01-27", "03-17", "05-05", "06-16", "07-28", "09-15", "10-27", "12-15"],
}

# CPI is typically released on the 2nd or 3rd Tuesday-Wednesday of the month
# PPI is typically released on the 2nd or 3rd Tuesday-Thursday of the month
# For simplicity, we use known 2025-2027 dates where available, else estimate.
# These are approximate — the BLS announces exact dates ~1 year ahead.

CPI_DATES = {
    2025: ["01-15", "02-12", "03-12", "04-10", "05-13", "06-11", "07-11", "08-12", "09-10", "10-14", "11-12", "12-10"],
    2026: ["01-14", "02-11", "03-11", "04-14", "05-12", "06-10", "07-14", "08-12", "09-10", "10-13", "11-10", "12-09"],
}

PPI_DATES = {
    2025: ["01-14", "02-13", "03-13", "04-11", "05-15", "06-12", "07-15", "08-14", "09-11", "10-15", "11-13", "12-11"],
    2026: ["01-15", "02-12", "03-12", "04-09", "05-14", "06-11", "07-16", "08-13", "09-15", "10-14", "11-12", "12-10"],
}

# Nonfarm payrolls: first Friday of the month
def _first_friday(year, month):
    first = date(year, month, 1)
    offset = (4 - first.weekday()) % 7
    return first + timedelta(days=offset)


def generate_economic_events(year):
    """Generate predictable economic/market events for a given year."""
    events = []

    # FOMC meetings
    if year in FOMC_DATES:
        for md in FOMC_DATES[year]:
            events.append({
                "title": "FOMC Meeting",
                "date": f"{year}-{md}",
                "time": "14:00",
                "category": "fomc",
            })

    # Monthly options expiration (third Friday)
    for month in range(1, 13):
        opex = _third_friday(year, month)
        events.append({
            "title": "Monthly OPEX",
            "date": opex.isoformat(),
            "time": "16:00",
            "category": "opex",
        })

    # Quad witching (third Friday of March, June, September, December)
    for month in [3, 6, 9, 12]:
        qw = _third_friday(year, month)
        # Replace the monthly OPEX with quad witching for these months
        events = [e for e in events if not (e["date"] == qw.isoformat() and e["category"] == "opex")]
        events.append({
            "title": "Quad Witching",
            "date": qw.isoformat(),
            "time": "16:00",
            "category": "opex",
        })

    # CPI releases
    if year in CPI_DATES:
        for md in CPI_DATES[year]:
            events.append({
                "title": "CPI Release",
                "date": f"{year}-{md}",
                "time": "08:30",
                "category": "economic",
            })

    # PPI releases
    if year in PPI_DATES:
        for md in PPI_DATES[year]:
            events.append({
                "title": "PPI Release",
                "date": f"{year}-{md}",
                "time": "08:30",
                "category": "economic",
            })

    # Nonfarm Payrolls (first Friday of each month)
    for month in range(1, 13):
        nfp = _first_friday(year, month)
        events.append({
            "title": "Nonfarm Payrolls",
            "date": nfp.isoformat(),
            "time": "08:30",
            "category": "economic",
        })

    return events


def ensure_economic_events(start_date, end_date):
    """Insert auto economic events for the date range, skipping already-inserted ones."""
    conn = get_connection()
    start_year = int(start_date[:4])
    end_year = int(end_date[:4])

    for year in range(start_year, end_year + 1):
        events = generate_economic_events(year)
        for evt in events:
            if evt["date"] < start_date or evt["date"] > end_date:
                continue
            # Check if this auto event already exists
            existing = conn.execute(
                "SELECT id FROM calendar_events WHERE title = ? AND date = ? AND auto = 1",
                (evt["title"], evt["date"])
            ).fetchone()
            if not existing:
                evt_id = str(uuid.uuid4())
                conn.execute(
                    "INSERT INTO calendar_events (id, title, date, time, category, auto) VALUES (?, ?, ?, ?, ?, 1)",
                    (evt_id, evt["title"], evt["date"], evt["time"], evt["category"])
                )
                log_change("calendar_events", {"id": evt_id}, "upsert", {
                    "id": evt_id, "title": evt["title"], "date": evt["date"],
                    "time": evt["time"], "category": evt["category"], "auto": 1
                })

    conn.commit()
    conn.close()

# ── Task Runs & Logs ──

def create_task_run(task_name):
    conn = get_connection()
    from datetime import datetime
    now = datetime.now().isoformat(timespec="seconds")
    cursor = conn.execute(
        "INSERT INTO task_runs (task_name, status, started_at) VALUES (?, 'running', ?)",
        (task_name, now)
    )
    run_id = cursor.lastrowid
    conn.commit()
    row = dict(conn.execute("SELECT * FROM task_runs WHERE id = ?", (run_id,)).fetchone())
    conn.close()
    return row

def finish_task_run(run_id, status="completed"):
    conn = get_connection()
    from datetime import datetime
    now = datetime.now().isoformat(timespec="seconds")
    conn.execute(
        "UPDATE task_runs SET status = ?, finished_at = ? WHERE id = ?",
        (status, now, run_id)
    )
    conn.commit()
    conn.close()

def get_task_runs(limit=50):
    conn = get_connection()
    cursor = conn.execute("SELECT * FROM task_runs ORDER BY id DESC LIMIT ?", (limit,))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

def append_task_log(run_id, task_name, message):
    conn = get_connection()
    from datetime import datetime
    now = datetime.now().isoformat(timespec="seconds")
    cursor = conn.execute(
        "INSERT INTO task_logs (run_id, task_name, message, created_at) VALUES (?, ?, ?, ?)",
        (run_id, task_name, message, now)
    )
    log_id = cursor.lastrowid
    conn.commit()
    row = dict(conn.execute("SELECT * FROM task_logs WHERE id = ?", (log_id,)).fetchone())
    conn.close()
    return row

def get_task_logs(task_name=None, limit=500, since_id=None):
    conn = get_connection()
    conditions = []
    params = []
    if task_name:
        conditions.append("task_name = ?")
        params.append(task_name)
    if since_id is not None:
        conditions.append("id > ?")
        params.append(since_id)
    where = (" WHERE " + " AND ".join(conditions)) if conditions else ""
    params.append(limit)
    cursor = conn.execute(f"SELECT * FROM task_logs{where} ORDER BY id ASC LIMIT ?", params)
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

sync_schema()
