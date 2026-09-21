"""
Sprint 6, Day 40: GET /api/v1/screener
"""

import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(BASE_DIR / "src" / "screener"))
sys.path.insert(0, str(BASE_DIR / "src" / "analytics"))

import math

from engine import run_screener  #type:ignore


def _sanitize_records(records):
    """
    pandas' df.where(df.notna(), None) doesn't actually stick on float64
    columns -- assigning None back into a float column silently reverts to
    NaN (a well-known pandas gotcha), and NaN isn't valid JSON. Sanitizing
    the already-converted records instead, which isn't dtype-constrained.
    """
    for record in records:
        for key, value in record.items():
            if isinstance(value, float) and math.isnan(value):
                record[key] = None
    return records


router = APIRouter()

# API param name -> engine.py's screener_config.yaml filter key
PARAM_TO_FILTER_KEY = {
    "min_roe": "roe_min",
    "max_de": "de_max",
    "min_fcf": "fcf_min",
    "min_rev_cagr_5yr": "revenue_cagr_5yr_min",
    "min_pat_cagr_5yr": "pat_cagr_5yr_min",
    "max_pe": "pe_max",
}


@router.get("/screener")
def get_screener(
    min_roe: str | None = None,
    max_de: str | None = None,
    min_fcf: str | None = None,
    sector: str | None = None,
    min_rev_cagr_5yr: str | None = None,
    min_pat_cagr_5yr: str | None = None,
    max_pe: str | None = None,
):
    """Get screener for the given min_roe, max_de, min_fcf, sector, min_rev_cagr_5yr, min_pat_cagr_5yr, max_pe."""
    raw_params = {
        "min_roe": min_roe,
        "max_de": max_de,
        "min_fcf": min_fcf,
        "min_rev_cagr_5yr": min_rev_cagr_5yr,
        "min_pat_cagr_5yr": min_pat_cagr_5yr,
        "max_pe": max_pe,
    }

    filters_dict = {}
    for param_name, raw_value in raw_params.items():
        if raw_value is None:
            continue
        try:
            threshold = float(raw_value)
        except ValueError:
            raise HTTPException(
                status_code=400, detail=f"Invalid value for '{param_name}': '{raw_value}' is not a number"
            )
        filters_dict[PARAM_TO_FILTER_KEY[param_name]] = threshold

    result_df = run_screener(filters_dict)

    if sector:
        if "broad_sector" not in result_df.columns:
            raise HTTPException(
                status_code=400, detail="Sector filtering unavailable — broad_sector column missing"
            )
        result_df = result_df[result_df["broad_sector"] == sector]

    result_df = result_df.where(result_df.notna(), None)
    columns = [
        "company_id",
        "broad_sector",
        "composite_quality_score",
        "return_on_equity_pct",
        "debt_to_equity",
        "free_cash_flow_cr",
        "revenue_cagr_5yr",
        "pat_cagr_5yr",
        "pe_ratio",
    ]
    available_columns = [c for c in columns if c in result_df.columns]

    return {
        "count": len(result_df),
        "filters_applied": filters_dict,
        "sector_filter": sector,
        "companies": _sanitize_records(result_df[available_columns].to_dict(orient="records")),
    }
