"""
Sprint 6, Day 40: GET /api/v1/sectors, GET /api/v1/sectors/{sector}/companies
"""

from fastapi import APIRouter, Depends, HTTPException

from src.api.database import get_db_connection

router = APIRouter()


@router.get("/sectors")
def list_sectors(conn=Depends(get_db_connection)):
    """List sectors for the given conn."""
    sector_names = [
        r["broad_sector"]
        for r in conn.execute("SELECT DISTINCT broad_sector FROM sectors ORDER BY broad_sector").fetchall()
    ]

    results = []
    for sector_name in sector_names:
        rows = conn.execute(
            """
            SELECT fr.return_on_equity_pct, fr.debt_to_equity, mc.pe_ratio
            FROM sectors s
            JOIN companies c ON c.id = s.company_id
            LEFT JOIN (
                SELECT company_id, MAX(year) AS latest_year FROM financial_ratios GROUP BY company_id
            ) latest_fr ON latest_fr.company_id = s.company_id
            LEFT JOIN financial_ratios fr ON fr.company_id = latest_fr.company_id AND fr.year = latest_fr.latest_year
            LEFT JOIN (
                SELECT company_id, MAX(year) AS latest_year FROM market_cap GROUP BY company_id
            ) latest_mc ON latest_mc.company_id = s.company_id
            LEFT JOIN market_cap mc ON mc.company_id = s.company_id AND mc.year = latest_mc.latest_year
            WHERE s.broad_sector = ?
        """,
            (sector_name,),
        ).fetchall()

        roe_values = sorted(r["return_on_equity_pct"] for r in rows if r["return_on_equity_pct"] is not None)
        de_values = sorted(r["debt_to_equity"] for r in rows if r["debt_to_equity"] is not None)
        pe_values = sorted(r["pe_ratio"] for r in rows if r["pe_ratio"] is not None)

        def median(values):
            """Median for the given values."""
            n = len(values)
            if n == 0:
                return None
            mid = n // 2
            return values[mid] if n % 2 else (values[mid - 1] + values[mid]) / 2

        results.append(
            {
                "broad_sector": sector_name,
                "company_count": len(rows),
                "median_roe": median(roe_values),
                "median_pe": median(pe_values),
                "median_de": median(de_values),
            }
        )

    return {
        "count": len(results),
        "note": "10 sectors in this dataset, not 11 — see module docstring",
        "sectors": results,
    }


@router.get("/sectors/{sector_name}/companies")
def get_sector_companies(sector_name: str, conn=Depends(get_db_connection)):
    """Get sector companies for the given sector_name, conn."""
    known_sectors = {
        r["broad_sector"] for r in conn.execute("SELECT DISTINCT broad_sector FROM sectors").fetchall()
    }
    if sector_name not in known_sectors:
        raise HTTPException(status_code=404, detail=f"Sector '{sector_name}' not found")

    rows = conn.execute(
        """
        SELECT s.company_id, c.company_name, s.sub_sector,
               fr.return_on_equity_pct, fr.debt_to_equity, fr.operating_profit_margin_pct,
               fr.revenue_cagr_5yr, fr.pat_cagr_5yr
        FROM sectors s
        JOIN companies c ON c.id = s.company_id
        LEFT JOIN (
            SELECT company_id, MAX(year) AS latest_year FROM financial_ratios GROUP BY company_id
        ) latest ON latest.company_id = s.company_id
        LEFT JOIN financial_ratios fr ON fr.company_id = latest.company_id AND fr.year = latest.latest_year
        WHERE s.broad_sector = ?
        ORDER BY c.company_name
    """,
        (sector_name,),
    ).fetchall()

    return {"broad_sector": sector_name, "count": len(rows), "companies": [dict(r) for r in rows]}
