"""
Sprint 6, Day 38: SQLite connection function shared by every router.
"""

import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "db" / "nifty100.db"

ALL_TABLES = [
    "companies", "profitandloss", "balancesheet", "cashflow", "analysis",
    "documents", "prosandcons", "sectors", "stock_prices", "market_cap",
    "peer_groups", "financial_ratios", "peer_percentiles",
]


def get_db_connection():
    """
    FastAPI dependency: yields a SQLite connection per-request, closed
    afterward. row_factory=sqlite3.Row so routers can access columns by
    name (row["company_id"]) instead of positional index.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()