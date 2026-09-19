"""
Sprint 6, Day 38: GET /api/v1/health
"""

import time
from fastapi import APIRouter, Depends

from src.api.database import ALL_TABLES, get_db_connection

router = APIRouter()

SERVER_START_TIME = time.time()
VERSION = "1.0.0"


@router.get("/health")
def get_health(conn=Depends(get_db_connection)):
    db_row_counts = {}
    for table in ALL_TABLES:
        cursor = conn.execute(f"SELECT COUNT(*) AS cnt FROM {table}")
        db_row_counts[table] = cursor.fetchone()["cnt"]

    return {
        "status": "ok",
        "db_row_counts": db_row_counts,
        "uptime_seconds": round(time.time() - SERVER_START_TIME, 2),
        "version": VERSION,
    }