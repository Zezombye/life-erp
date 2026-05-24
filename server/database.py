import sqlite3
import json
import os
import calendar as cal
from datetime import date, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), "life_erp.db")
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "database.json")

def load_schema():
    with open(SCHEMA_PATH, "r") as f:
        return json.load(f)

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
            for col_name, col_opts in columns.items():
                col_type = col_opts["type"]
                pk = " PRIMARY KEY" if col_opts.get("primary_key") else ""
                col_defs.append(f"{col_name} {col_type}{pk}")
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

def get_valid_columns(table_name):
    """Return the set of non-PK column names for a table from the schema."""
    schema = load_schema()
    table_def = schema[table_name]
    return {
        name for name, opts in table_def["columns"].items()
        if not opts.get("primary_key")
    }

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
    return row

DEFAULT_SETTINGS = {
    "work_mn": "300",
    "watchlist": "AAPL,MSFT,GOOGL,AMZN,TSLA",
}

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
    # For the 'type' and 'notes' columns, store as text; others as numeric
    conn.execute(
        f"UPDATE workouts SET {column} = ? WHERE date = ?",
        (value, date_str)
    )
    conn.commit()
    cursor = conn.execute("SELECT * FROM workouts WHERE date = ?", (date_str,))
    row = dict(cursor.fetchone())
    conn.close()
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
    cursor = conn.execute(
        "INSERT INTO chores (title, interval_days) VALUES (?, ?)",
        (title, interval_days)
    )
    chore_id = cursor.lastrowid
    conn.commit()
    row = dict(conn.execute("SELECT * FROM chores WHERE id = ?", (chore_id,)).fetchone())
    conn.close()
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
    return dict(row)

def delete_chore(chore_id):
    conn = get_connection()
    conn.execute("DELETE FROM chores WHERE id = ?", (chore_id,))
    conn.commit()
    conn.close()

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
    now = date.today().isoformat()
    cursor = conn.execute(
        "INSERT INTO todos (title, status, created_at) VALUES (?, 'open', ?)",
        (title, now)
    )
    todo_id = cursor.lastrowid
    conn.commit()
    row = dict(conn.execute("SELECT * FROM todos WHERE id = ?", (todo_id,)).fetchone())
    conn.close()
    return row

def update_todo(todo_id, title):
    conn = get_connection()
    conn.execute("UPDATE todos SET title = ? WHERE id = ?", (title, todo_id))
    conn.commit()
    row = conn.execute("SELECT * FROM todos WHERE id = ?", (todo_id,)).fetchone()
    conn.close()
    if not row:
        raise ValueError(f"Todo {todo_id} not found")
    return dict(row)

def set_todo_status(todo_id, status):
    conn = get_connection()
    updates = "status = ?"
    params = [status]
    if status == "closed":
        updates += ", closed_at = ?"
        params.append(date.today().isoformat())
    else:
        updates += ", closed_at = NULL"
    params.append(todo_id)
    conn.execute(f"UPDATE todos SET {updates} WHERE id = ?", params)
    conn.commit()
    row = conn.execute("SELECT * FROM todos WHERE id = ?", (todo_id,)).fetchone()
    conn.close()
    if not row:
        raise ValueError(f"Todo {todo_id} not found")
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
    now = date.today().isoformat()
    cursor = conn.execute(
        "INSERT INTO todo_messages (todo_id, content, created_at, updated_at) VALUES (?, ?, ?, ?)",
        (todo_id, content, now, now)
    )
    msg_id = cursor.lastrowid
    conn.commit()
    row = dict(conn.execute("SELECT * FROM todo_messages WHERE id = ?", (msg_id,)).fetchone())
    conn.close()
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
    return dict(row)

def delete_todo_message(message_id):
    conn = get_connection()
    conn.execute("DELETE FROM todo_messages WHERE id = ?", (message_id,))
    conn.commit()
    conn.close()

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
    cursor = conn.execute(
        "INSERT INTO calendar_events (title, date, time, category, auto) VALUES (?, ?, ?, ?, 0)",
        (title, evt_date, evt_time, category)
    )
    evt_id = cursor.lastrowid
    conn.commit()
    row = dict(conn.execute("SELECT * FROM calendar_events WHERE id = ?", (evt_id,)).fetchone())
    conn.close()
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
    return dict(row)

def delete_calendar_event(evt_id):
    conn = get_connection()
    conn.execute("DELETE FROM calendar_events WHERE id = ? AND auto = 0", (evt_id,))
    conn.commit()
    conn.close()


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
                conn.execute(
                    "INSERT INTO calendar_events (title, date, time, category, auto) VALUES (?, ?, ?, ?, 1)",
                    (evt["title"], evt["date"], evt["time"], evt["category"])
                )

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
