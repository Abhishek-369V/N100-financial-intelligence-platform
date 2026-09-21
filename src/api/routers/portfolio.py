"""
Sprint 6, Day 40: GET /api/v1/portfolio/stats
"""

from pathlib import Path

import pandas as pd
from fastapi import APIRouter, HTTPException

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
STATS_PATH = BASE_DIR / "output" / "portfolio_stats.csv"


@router.get("/portfolio/stats")
def get_portfolio_stats():
    """Get portfolio stats."""
    if not STATS_PATH.exists():
        raise HTTPException(
            status_code=404,
            detail="portfolio_stats.csv not found — run src/analytics/cluster_profiling.py (Sprint 6 Day 37) first",
        )

    df = pd.read_csv(STATS_PATH)
    return {"count": len(df), "portfolio_stats": df.to_dict(orient="records")}
