import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent  
DB_PATH = BASE_DIR / "db" / "nifty100.db"
SQL_PATH = BASE_DIR / "notebooks" / "exploratory_queries.sql"

print(f"Connecting to: {DB_PATH}")
print(f"DB exists: {DB_PATH.exists()}")

conn = sqlite3.connect(str(DB_PATH))
cursor = conn.cursor()

sql_script = SQL_PATH.read_text()

# Split into individual statements, strip comments and blank lines
raw_statements = sql_script.split(";")
queries = []
for stmt in raw_statements:
    lines = [line for line in stmt.split("\n") if not line.strip().startswith("--")]
    cleaned = "\n".join(lines).strip()
    if cleaned:
        queries.append(cleaned)

print(f"Found {len(queries)} queries to run.\n")

for i, query in enumerate(queries, 1):
    print(f"--- Query {i} ---")
    print(query[:100], "...")  # show first 100 chars so you know which query ran
    try:
        cursor.execute(query)
        rows = cursor.fetchall()
        col_names = [desc[0] for desc in cursor.description] if cursor.description else []
        print("Columns:", col_names)
        print(f"Row count: {len(rows)}")
        for row in rows[:5]:
            print(row)
    except Exception as e:
        print(f"❌ ERROR on query {i}: {e}")
    print()

conn.close()
print("Done.")