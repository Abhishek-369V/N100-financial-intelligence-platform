"""GET /api/v1/screener -- the backend source of truth for screening."""

import math
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent

from src.api.database import get_db_connection
from src.screener.engine import run_screener

router = APIRouter()

# API parameter -> analyst-editable screener_config.yaml filter key.
PARAM_TO_FILTER_KEY = {
    "min_roe": "roe_min",
    "max_de": "de_max",
    "min_fcf": "fcf_min",
    "min_rev_cagr_5yr": "revenue_cagr_5yr_min",
    "min_pat_cagr_5yr": "pat_cagr_5yr_min",
    "min_opm": "opm_min",
    "max_pe": "pe_max",
    "max_pb": "pb_max",
    "min_dividend_yield": "dividend_yield_min",
    "min_icr": "icr_min",
}


def _sanitize_records(records):
    """Convert NaN/inf floats to JSON-safe nulls."""
    for record in records:
        for key, value in record.items():
            if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
                record[key] = None
    return records


@router.get("/screener")
def get_screener(
    min_roe: str | None = None,
    max_de: str | None = None,
    min_fcf: str | None = None,
    sector: str | None = None,
    min_rev_cagr_5yr: str | None = None,
    min_pat_cagr_5yr: str | None = None,
    min_opm: str | None = None,
    max_pe: str | None = None,
    max_pb: str | None = None,
    min_dividend_yield: str | None = None,
    min_icr: str | None = None,
    conn=Depends(get_db_connection),
):
    """Run the same screening engine used by the analytical application."""
    raw_params = {
        "min_roe": min_roe,
        "max_de": max_de,
        "min_fcf": min_fcf,
        "min_rev_cagr_5yr": min_rev_cagr_5yr,
        "min_pat_cagr_5yr": min_pat_cagr_5yr,
        "min_opm": min_opm,
        "max_pe": max_pe,
        "max_pb": max_pb,
        "min_dividend_yield": min_dividend_yield,
        "min_icr": min_icr,
    }

    filters_dict = {}
    for param_name, raw_value in raw_params.items():
        if raw_value is None:
            continue
        try:
            threshold = float(raw_value)
        except (TypeError, ValueError):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid value for '{param_name}': '{raw_value}' is not a number",
            )
        filters_dict[PARAM_TO_FILTER_KEY[param_name]] = threshold

    result_df = run_screener(filters_dict)

    if sector:
        if "broad_sector" not in result_df.columns:
            raise HTTPException(status_code=400, detail="Sector filtering unavailable — broad_sector column missing")
        result_df = result_df[result_df["broad_sector"] == sector]

    columns = [
        "company_id",
        "broad_sector",
        "composite_quality_score",
        "return_on_equity_pct",
        "roce_percentage",
        "net_profit_margin_pct",
        "debt_to_equity",
        "free_cash_flow_cr",
        "revenue_cagr_5yr",
        "pat_cagr_5yr",
        "operating_profit_margin_pct",
        "pe_ratio",
        "pb_ratio",
        "dividend_yield_pct",
        "interest_coverage",
        "sales",
    ]
    available_columns = [c for c in columns if c in result_df.columns]

    company_ids = result_df["company_id"].tolist()
    if company_ids:
        placeholders = ",".join("?" for _ in company_ids)
        names = conn.execute(
            f"SELECT id AS company_id, company_name FROM companies WHERE id IN ({placeholders})",
            company_ids,
        ).fetchall()
        name_map = {row["company_id"]: row["company_name"] for row in names}
        result_df = result_df.copy()
        result_df.insert(1, "company_name", result_df["company_id"].map(name_map))
        available_columns.insert(1, "company_name")

    return {
        "count": len(result_df),
        "filters_applied": filters_dict,
        "sector_filter": sector,
        "companies": _sanitize_records(result_df[available_columns].to_dict(orient="records")),
    }