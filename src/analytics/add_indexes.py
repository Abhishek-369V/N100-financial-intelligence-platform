"""
Sprint 6, Day 43 — SQLite query optimization: indexes on company_id and
year columns in large tables.

HONEST FINDING: measured before/after with 200 repeated query-pairs against the largest table (stock_prices, 5,520 rows). 
Baseline was already 0.28ms per query-pair -- SQLite's query planner handles a full scan over a few thousand rows 
essentially instantly regardless of an index. 
The "before adding indexes this was slow" story that might be expected here doesn't apply at this dataset's actual size. 
Added the indexes anyway (spec asks for it, and it's correct forward-looking practice -- this dataset is Nifty 100 today, 
and the same schema would matter a lot more at Nifty 500 or with years of intraday stock_prices data), 
but reporting the real, small measured difference rather than dramatizing it. 
See output/performance_notes.md for the full writeup.
"""

import sqlite3
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "db" / "nifty100.db"

# (table, columns) -- company_id and year are the two columns every router
# and analytics module filters/sorts on repeatedly (see src/api/routers/*.py, src/analytics/*.py) 
# for every table with meaningful row counts.
TABLES_TO_INDEX = [
    ("profitandloss", ["company_id", "year"]),
    ("balancesheet", ["company_id", "year"]),
    ("cashflow", ["company_id", "year"]),
    ("stock_prices", ["company_id", "year"]),
    ("market_cap", ["company_id", "year"]),
    ("financial_ratios", ["company_id", "year"]),
    ("documents", ["company_id"]),  # this table's year column is "Year" (capitalized) — see Day 40 gap
    ("peer_percentiles", ["company_id", "peer_group_name"]),
]


def measure_query_time(conn, n=200):
    start = time.perf_counter()
    for _ in range(n):
        conn.execute("SELECT * FROM stock_prices WHERE company_id = 'TCS'").fetchall()
        conn.execute("SELECT * FROM profitandloss WHERE company_id = 'TCS' AND year = '2024-03'").fetchall()
    return (time.perf_counter() - start) / n * 1000


def add_indexes():
    conn = sqlite3.connect(DB_PATH)

    before_ms = measure_query_time(conn)

    created = []
    for table, columns in TABLES_TO_INDEX:
        index_name = f"idx_{table}_{'_'.join(columns)}"
        column_list = ", ".join(f'"{c}"' for c in columns)
        conn.execute(f'CREATE INDEX IF NOT EXISTS {index_name} ON {table} ({column_list})')
        created.append(index_name)
    conn.commit()

    after_ms = measure_query_time(conn)
    conn.close()

    return created, before_ms, after_ms


if __name__ == "__main__":
    created, before_ms, after_ms = add_indexes()
    print(f"Indexes created: {len(created)}")
    for name in created:
        print(f"  {name}")
    print(f"\nBefore: {before_ms:.4f}ms per query-pair")
    print(f"After:  {after_ms:.4f}ms per query-pair")
    print(f"Difference is small at this dataset size (see module docstring) — "
          f"added as forward-looking practice, not a fix for an observed bottleneck.")