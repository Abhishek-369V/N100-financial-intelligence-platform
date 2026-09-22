"""
Sprint 6, Day 39: Company Data Endpoints
"""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse

from src.api.database import get_db_connection

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
TEARSHEET_DIR = BASE_DIR / "reports" / "tearsheets"


def row_to_dict(row):
    """Row to dict for the given row."""
    return dict(row) if row is not None else None


def rows_to_list(rows):
    """Rows to list for the given rows."""
    return [dict(r) for r in rows]


def get_latest_ratios_row(conn, ticker):
    """Get latest ratios row for the given conn, ticker."""
    cursor = conn.execute(
        "SELECT * FROM financial_ratios WHERE company_id = ? ORDER BY year DESC LIMIT 1", (ticker,)
    )
    return cursor.fetchone()


@router.get("/companies")
def list_companies(
    sector: str | None = None,
    market_cap_category: str | None = None,
    search: str | None = Query(None, description="Partial match on company name or ticker"),
    conn=Depends(get_db_connection),
):
    """List companies for the given sector, market_cap_category, search, conn."""
    query = """
        SELECT c.id, c.company_name, s.broad_sector, s.sub_sector,
               c.roce_percentage, s.market_cap_category
        FROM companies c
        LEFT JOIN sectors s ON s.company_id = c.id
        WHERE 1=1
    """
    params = []
    if sector:
        query += " AND s.broad_sector = ?"
        params.append(sector)
    if market_cap_category:
        query += " AND s.market_cap_category = ?"
        params.append(market_cap_category)
    if search:
        query += " AND (c.company_name LIKE ? OR c.id LIKE ?)"
        like = f"%{search}%"
        params.extend([like, like])

    rows = conn.execute(query, params).fetchall()

    # ROE pulled separately from financial_ratios (latest year) rather than
    # companies.roe_percentage -- see gap in sprint6_retro.md
    results = []
    for row in rows:
        ratios_row = get_latest_ratios_row(conn, row["id"])
        results.append(
            {
                "id": row["id"],
                "company_name": row["company_name"],
                "broad_sector": row["broad_sector"],
                "sub_sector": row["sub_sector"],
                "roe_pct": ratios_row["return_on_equity_pct"] if ratios_row else None,
                "roce_pct": row["roce_percentage"],
            }
        )

    return {"count": len(results), "companies": results}


@router.get("/companies/{ticker}")
def get_company_profile(ticker: str, conn=Depends(get_db_connection)):
    """Get company profile for the given ticker, conn."""
    company = conn.execute("SELECT * FROM companies WHERE id = ?", (ticker,)).fetchone()
    if company is None:
        raise HTTPException(status_code=404, detail=f"Company '{ticker}' not found")

    sector = conn.execute("SELECT * FROM sectors WHERE company_id = ?", (ticker,)).fetchone()
    latest_ratios = get_latest_ratios_row(conn, ticker)
    pros_cons = conn.execute(
        "SELECT pros, cons FROM prosandcons WHERE company_id = ? ORDER BY id DESC LIMIT 1",
        (ticker,),
    ).fetchone()

    return {
        "company": row_to_dict(company),
        "sector": row_to_dict(sector),
        "latest_year_kpis": row_to_dict(latest_ratios),
        "pros_cons": row_to_dict(pros_cons),
    }


def _apply_year_filter(query, params, from_year, to_year):
    """Apply year filter for the given query, params, from_year, to_year."""
    if from_year:
        query += " AND year >= ?"
        params.append(from_year)
    if to_year:
        query += " AND year <= ?"
        params.append(to_year)
    return query, params


@router.get("/companies/{ticker}/pl")
def get_profit_and_loss(
    ticker: str,
    from_year: str | None = Query(None, description="YYYY-MM"),
    to_year: str | None = Query(None, description="YYYY-MM"),
    conn=Depends(get_db_connection),
):
    """Get profit and loss for the given ticker, from_year, to_year, conn."""
    if conn.execute("SELECT 1 FROM companies WHERE id = ?", (ticker,)).fetchone() is None:
        raise HTTPException(status_code=404, detail=f"Company '{ticker}' not found")

    query = "SELECT * FROM profitandloss WHERE company_id = ?"
    params = [ticker]
    query, params = _apply_year_filter(query, params, from_year, to_year)
    query += " ORDER BY year"

    rows = conn.execute(query, params).fetchall()
    return {"company_id": ticker, "count": len(rows), "profit_and_loss": rows_to_list(rows)}


@router.get("/companies/{ticker}/bs")
def get_balance_sheet(
    ticker: str,
    from_year: str | None = Query(None, description="YYYY-MM"),
    to_year: str | None = Query(None, description="YYYY-MM"),
    conn=Depends(get_db_connection),
):
    """Get balance sheet for the given ticker, from_year, to_year, conn."""
    if conn.execute("SELECT 1 FROM companies WHERE id = ?", (ticker,)).fetchone() is None:
        raise HTTPException(status_code=404, detail=f"Company '{ticker}' not found")

    query = "SELECT * FROM balancesheet WHERE company_id = ?"
    params = [ticker]
    query, params = _apply_year_filter(query, params, from_year, to_year)
    query += " ORDER BY year"

    rows = conn.execute(query, params).fetchall()
    return {"company_id": ticker, "count": len(rows), "balance_sheet": rows_to_list(rows)}


@router.get("/companies/{ticker}/cashflow")
def get_cashflow(
    ticker: str,
    from_year: str | None = Query(None, description="YYYY-MM"),
    to_year: str | None = Query(None, description="YYYY-MM"),
    conn=Depends(get_db_connection),
):
    """Get cashflow for the given ticker, from_year, to_year, conn."""
    if conn.execute("SELECT 1 FROM companies WHERE id = ?", (ticker,)).fetchone() is None:
        raise HTTPException(status_code=404, detail=f"Company '{ticker}' not found")

    query = "SELECT * FROM cashflow WHERE company_id = ?"
    params = [ticker]
    query, params = _apply_year_filter(query, params, from_year, to_year)
    query += " ORDER BY year"

    rows = conn.execute(query, params).fetchall()
    return {"company_id": ticker, "count": len(rows), "cashflow": rows_to_list(rows)}


@router.get("/companies/{ticker}/ratios")
def get_ratios(
    ticker: str,
    year: str | None = Query(None, description="Single year, YYYY-MM. Omit for full history."),
    conn=Depends(get_db_connection),
):
    """Get ratios for the given ticker, year, conn."""
    if conn.execute("SELECT 1 FROM companies WHERE id = ?", (ticker,)).fetchone() is None:
        raise HTTPException(status_code=404, detail=f"Company '{ticker}' not found")

    if year:
        rows = conn.execute(
            "SELECT * FROM financial_ratios WHERE company_id = ? AND year = ?", (ticker, year)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM financial_ratios WHERE company_id = ? ORDER BY year", (ticker,)
        ).fetchall()

    return {"company_id": ticker, "count": len(rows), "ratios": rows_to_list(rows)}


@router.get("/companies/{ticker}/tearsheet")
def get_tearsheet(ticker: str, conn=Depends(get_db_connection)):
    """Get tearsheet for the given ticker, conn."""
    company = conn.execute("SELECT 1 FROM companies WHERE id = ?", (ticker,)).fetchone()
    if company is None:
        raise HTTPException(status_code=404, detail=f"Company '{ticker}' not found")

    tearsheet_path = TEARSHEET_DIR / f"{ticker}_tearsheet.pdf"
    if not tearsheet_path.exists():
        # Distinguish "no such company" from "company exists but was skipped"
        # (Sprint 5 Day 34's <3yrs-data skip rule) -- see module docstring gap #2.
        raise HTTPException(
            status_code=404,
            detail=f"'{ticker}' exists but has no tearsheet PDF (likely skipped in batch "
            f"generation for having fewer than 3 years of data — see output/skipped_tearsheets.csv)",
        )

    return FileResponse(
        path=str(tearsheet_path), media_type="application/pdf", filename=f"{ticker}_tearsheet.pdf"
    )