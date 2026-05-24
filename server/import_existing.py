"""Import existing.txt TSV data into the habits database."""
import re
import database

FRENCH_MONTHS = {
    "janvier": 1, "février": 2, "mars": 3, "avril": 4,
    "mai": 5, "juin": 6, "juillet": 7, "août": 8,
    "septembre": 9, "octobre": 10, "novembre": 11, "décembre": 12,
}

def parse_french_date(s):
    """Parse 'mardi 9 août 2022' → '2022-08-09'"""
    parts = s.strip().split()
    # parts: ['mardi', '9', 'août', '2022']
    day = int(parts[1])
    month = FRENCH_MONTHS[parts[2]]
    year = int(parts[3])
    return f"{year:04d}-{month:02d}-{day:02d}"

def parse_value(s, fmt):
    """Parse a cell value string into a number or None."""
    s = s.strip()
    if not s or s == "/":
        return None

    if fmt == "percentage":
        m = re.match(r"([\d.]+)%", s)
        return float(m.group(1)) if m else None

    if fmt == "minutes":
        m = re.match(r"(\d+)\s*mn", s)
        return float(m.group(1)) if m else None

    if fmt == "hours":
        m = re.match(r"(\d+)h(\d+)mn", s)
        if m:
            return float(int(m.group(1)) * 60 + int(m.group(2)))
        return None

    # raw number (weight)
    try:
        return float(s)
    except ValueError:
        return None

# Column order matches the TSV, with their parse formats
COLUMNS = [
    ("date", None),
    ("weight", "raw"),
    ("job", "minutes"),
    ("workout", "percentage"),
    ("business", "minutes"),
    ("reading_watching", "minutes"),
    ("misc", "minutes"),
    ("girls_family", "minutes"),
    ("mma", "minutes"),
    ("total", "percentage"),
    ("total_hours", "hours"),
]

def main():
    import os
    filepath = os.path.join(os.path.dirname(__file__), "existing.txt")

    conn = database.get_connection()
    count = 0

    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n\r")
            if not line.strip():
                continue

            fields = line.split("\t")
            date_str = parse_french_date(fields[0])

            # Upsert the row
            conn.execute(
                "INSERT INTO habits (date) VALUES (?) ON CONFLICT(date) DO NOTHING",
                (date_str,)
            )

            # Set each column value
            for i, (col_name, fmt) in enumerate(COLUMNS):
                if col_name == "date":
                    continue
                raw = fields[i] if i < len(fields) else ""
                value = parse_value(raw, fmt)
                if value is not None:
                    conn.execute(
                        f"UPDATE habits SET {col_name} = ? WHERE date = ?",
                        (value, date_str)
                    )

            count += 1

    conn.commit()
    conn.close()
    print(f"Imported {count} rows")

if __name__ == "__main__":
    main()
