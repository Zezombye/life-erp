"""
One-time migration: convert INTEGER PRIMARY KEY → TEXT UUID for synced tables.

Tables migrated:
  - habit_timer
  - workout_presets
  - chores
  - todos
  - todo_messages  (also updates todo_id FK)
  - calendar_events

Run from the server/ directory:
    python migrate_to_uuid.py

A backup is created at life_erp.db.bak before any changes.
"""

import sqlite3
import shutil
import os
import uuid

DB_PATH = os.path.join(os.path.dirname(__file__), "life_erp.db")
BACKUP_PATH = DB_PATH + ".bak"

# Tables to migrate: (table_name, [fk_updates], [columns_to_force_text])
# fk_updates: list of (child_table, child_fk_column) that reference this table's old id
# columns_to_force_text: additional columns in THIS table to convert to TEXT (for FK columns)
# Order matters: child tables must come before parent tables that update their FKs
TABLES = [
    ("habit_timer", [], []),
    ("workout_presets", [], []),
    ("chores", [], []),
    ("todo_messages", [], ["todo_id"]),
    ("todos", [("todo_messages", "todo_id")], []),
    ("calendar_events", [], []),
]


def migrate():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}, nothing to migrate.")
        return

    # Backup
    shutil.copy2(DB_PATH, BACKUP_PATH)
    print(f"Backup created at {BACKUP_PATH}")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = OFF")

    for table_name, fk_updates, force_text_cols in TABLES:
        print(f"\nMigrating {table_name}...")

        # Check if table exists
        exists = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,)
        ).fetchone()
        if not exists:
            print(f"  Table {table_name} does not exist, skipping.")
            continue

        # Check if id column is already TEXT
        pragma = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        id_col = next((c for c in pragma if c["name"] == "id"), None)
        if id_col and id_col["type"].upper() == "TEXT":
            print(f"  Already migrated (id is TEXT), skipping.")
            continue

        # Read all rows
        rows = conn.execute(f"SELECT * FROM {table_name}").fetchall()
        columns = [desc["name"] for desc in pragma]
        print(f"  {len(rows)} rows to migrate")

        # Build old_id -> new_uuid mapping
        id_map = {}
        for row in rows:
            old_id = row["id"]
            new_id = str(uuid.uuid4())
            id_map[old_id] = new_id

        # Recreate table with TEXT id + any forced TEXT columns
        force_text = {"id", *force_text_cols}
        col_defs = []
        pk_cols = []
        for col_info in pragma:
            col_name = col_info["name"]
            col_type = col_info["type"]
            if col_name in force_text:
                col_type = "TEXT"
            col_defs.append(f"{col_name} {col_type}")
            if col_info["pk"]:
                pk_cols.append(col_name)

        # Drop old table and recreate
        conn.execute(f"DROP TABLE {table_name}")
        create_sql = f"CREATE TABLE {table_name} ({', '.join(col_defs)}"
        if pk_cols:
            create_sql += f", PRIMARY KEY ({', '.join(pk_cols)})"
        create_sql += ")"
        conn.execute(create_sql)

        # Re-insert with new UUIDs
        if rows:
            placeholders = ", ".join("?" for _ in columns)
            insert_sql = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
            for row in rows:
                values = []
                for col in columns:
                    val = row[col]
                    if col == "id":
                        val = id_map[val]
                    values.append(val)
                conn.execute(insert_sql, values)

        # Update FK references in child tables
        for child_table, child_fk_col in fk_updates:
            child_exists = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (child_table,)
            ).fetchone()
            if not child_exists:
                continue

            # Check if child FK column needs type change
            child_pragma = conn.execute(f"PRAGMA table_info({child_table})").fetchall()
            fk_col_info = next((c for c in child_pragma if c["name"] == child_fk_col), None)
            if not fk_col_info:
                continue

            print(f"  Updating FK {child_table}.{child_fk_col}...")
            for old_id, new_id in id_map.items():
                conn.execute(
                    f"UPDATE {child_table} SET {child_fk_col} = ? WHERE {child_fk_col} = ?",
                    (new_id, old_id)
                )

        print(f"  Done: {len(id_map)} rows migrated")

    # Also clean up _change_log entries that reference old integer PKs
    # These are stale anyway after migration
    try:
        conn.execute("DELETE FROM _change_log")
        print("\nCleared _change_log (stale after PK migration)")
    except Exception:
        pass

    conn.commit()
    conn.close()
    print("\nMigration complete!")


if __name__ == "__main__":
    migrate()
