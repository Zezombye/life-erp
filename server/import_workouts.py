"""Import workout data from workout.txt into the SQLite database."""
import sqlite3
import os
import re

DB_PATH = os.path.join(os.path.dirname(__file__), "life_erp.db")
TXT_PATH = os.path.join(os.path.dirname(__file__), "workout.txt")

# Map TSV header columns to DB columns
COL_MAP = {
    "1-1 wt": "e1s1_wt", "1-1 reps": "e1s1_reps",
    "1-2 wt": "e1s2_wt", "1-2 reps": "e1s2_reps",
    "1-3 wt": "e1s3_wt", "1-3 reps": "e1s3_reps",
    "2-1 wt": "e2s1_wt", "2-1 reps": "e2s1_reps",
    "2-2 wt": "e2s2_wt", "2-2 reps": "e2s2_reps",
    "2-3 wt": "e2s3_wt", "2-3 reps": "e2s3_reps",
    "3-1 wt": "e3s1_wt", "3-1 reps": "e3s1_reps",
    "3-2 wt": "e3s2_wt", "3-2 reps": "e3s2_reps",
    "3-3 wt": "e3s3_wt", "3-3 reps": "e3s3_reps",
    "4-1 wt": "e4s1_wt", "4-1 reps": "e4s1_reps",
    "4-2 wt": "e4s2_wt", "4-2 reps": "e4s2_reps",
    "4-3 wt": "e4s3_wt", "4-3 reps": "e4s3_reps",
}


def parse_date(s):
    """Convert DD/MM/YYYY to YYYY-MM-DD."""
    d, m, y = s.split("/")
    return f"{y}-{m}-{d}"


def parse_weight(s):
    """Strip 'kg' suffix and return float, or None."""
    s = s.strip()
    if not s:
        return None
    s = s.replace("kg", "").strip()
    try:
        return float(s)
    except ValueError:
        return None


def parse_reps(s):
    """Return float or None."""
    s = s.strip()
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def main():
    with open(TXT_PATH, "r", encoding="utf-8") as f:
        lines = f.readlines()

    headers = lines[0].strip().split("\t")
    print(f"Headers: {headers}")

    conn = sqlite3.connect(DB_PATH)
    imported = 0
    skipped = 0

    for line_no, line in enumerate(lines[1:], start=2):
        parts = line.rstrip("\n").split("\t")
        if not parts or not parts[0].strip():
            continue

        date_str = parse_date(parts[0].strip())
        workout_type = parts[1].strip() if len(parts) > 1 else None

        # Skip rows that are just header labels mid-file
        if workout_type and workout_type.lower() in ("pullups", "day"):
            workout_type = None

        # Build column values
        values = {"date": date_str, "type": workout_type or None}

        for i, header in enumerate(headers):
            if header in COL_MAP:
                raw = parts[i] if i < len(parts) else ""
                db_col = COL_MAP[header]
                if "wt" in db_col:
                    values[db_col] = parse_weight(raw)
                else:
                    values[db_col] = parse_reps(raw)

        # Notes is the last column
        notes_idx = headers.index("Notes") if "Notes" in headers else -1
        if notes_idx >= 0 and notes_idx < len(parts):
            notes = parts[notes_idx].strip()
            values["notes"] = notes if notes else None
        else:
            values["notes"] = None

        # Check if row has any actual data beyond date
        has_data = values["type"] is not None or values["notes"] is not None or any(
            v is not None for k, v in values.items() if k not in ("date", "type", "notes")
        )

        cols = list(values.keys())
        placeholders = ", ".join("?" for _ in cols)
        col_names = ", ".join(cols)
        updates = ", ".join(f"{c} = excluded.{c}" for c in cols if c != "date")

        conn.execute(
            f"INSERT INTO workouts ({col_names}) VALUES ({placeholders}) "
            f"ON CONFLICT(date) DO UPDATE SET {updates}",
            [values[c] for c in cols],
        )
        imported += 1

    conn.commit()
    total = conn.execute("SELECT COUNT(*) FROM workouts").fetchone()[0]
    non_empty = conn.execute(
        "SELECT COUNT(*) FROM workouts WHERE type IS NOT NULL"
    ).fetchone()[0]
    conn.close()
    print(f"Imported {imported} rows. Total rows in DB: {total}, with data: {non_empty}")


if __name__ == "__main__":
    main()
