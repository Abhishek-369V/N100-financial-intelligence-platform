"""
Sprint 6, Day 40: GET /api/v1/market-cap/{ticker}
"""

from fastapi import APIRouter, Depends, HTTPException

from src.api.database import get_db_connection

router = APIRouter()


@router.get("/market-cap/{ticker}")
def get_market_cap_history(ticker: str, conn=Depends(get_db_connection)):
    if conn.execute("SELECT 1 FROM companies WHERE id = ?", (ticker,)).fetchone() is None:
        raise HTTPException(status_code=404, detail=f"Company '{ticker}' not found")

    rows = conn.execute("""
        SELECT year, market_cap_crore, enterprise_value_crore, pe_ratio, pb_ratio,
               ev_ebitda, dividend_yield_pct
        FROM market_cap
        WHERE company_id = ?
        ORDER BY year
    """, (ticker,)).fetchall()

    return {"company_id": ticker, "count": len(rows), "market_cap_history": [dict(r) for r in rows]}
