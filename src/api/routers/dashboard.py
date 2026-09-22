"""Dashboard-specific read models used by the Streamlit frontend.

These endpoints keep page-level aggregation in the backend 
so the Streamlit process --> does not need direct access to SQLite or to the analytics data sources.
"""

from __future__ import annotations

import math

import pandas as pd
from fastapi import APIRouter, Depends, Query

from src.analytics.cashflow_kpis import classify_capital_allocation
from src.api.database import get_db_connection
from src.screener.composite_score import winsorize
from src.screener.engine import run_screener

router = APIRouter()


def _sanitize_records(records: list[dict]) -> list[dict]:
    """Replace NaN/inf values with JSON-safe nulls."""
    for record in records:
        for key, value in record.items():
            if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
                record[key] = None
    return records


@router.get("/dashboard/home")
def get_home_dashboard(
    year: int = Query(2024, ge=2019, le=2024),
    conn=Depends(get_db_connection),
):
    """Return all data required by the Home dashboard for one calendar year."""
    companies = pd.read_sql_query(
        "SELECT id AS company_id, company_name FROM companies ORDER BY id", conn
    )
    ratios = pd.read_sql_query("SELECT * FROM financial_ratios", conn)
    sectors = pd.read_sql_query("SELECT company_id, broad_sector FROM sectors", conn)
    market_cap = pd.read_sql_query(
        "SELECT company_id, pe_ratio FROM market_cap WHERE year = ?", conn, params=(f"{year}-03",)
    )

    ratios["calendar_year"] = ratios["year"].str[:4].astype(int)
    ratios_year = (
        ratios[ratios["calendar_year"] == year]
        .sort_values("year")
        .groupby("company_id")
        .last()
        .reset_index()
    )

    if ratios_year.empty:
        return {
            "year": year,
            "has_data": False,
            "company_count": int(companies["company_id"].nunique()),
            "companies_with_ratio_data": 0,
            "kpis": {},
            "sector_breakdown": [],
            "top5": [],
        }

    roe = ratios_year["return_on_equity_pct"]
    avg_roe_raw = roe.mean()
    avg_roe_winsorized = winsorize(roe).mean()
    debt_free_count = int((ratios_year["debt_to_equity"] == 0).sum())
    median_de = ratios_year["debt_to_equity"].median()
    median_rev_cagr = ratios_year["revenue_cagr_5yr"].median()
    median_pe = market_cap["pe_ratio"].median() if not market_cap.empty else None

    sector_counts = sectors["broad_sector"].value_counts().rename_axis("broad_sector").reset_index(name="count")

    # Preserve the existing Home semantics: the composite score is based on
    # each company's latest available data, independent of the year selector.
    scored = run_screener({})
    top5 = (
        scored.merge(companies, on="company_id", how="left")
        .sort_values("composite_quality_score", ascending=False, na_position="last")
        .head(5)[["company_id", "company_name", "composite_quality_score"]]
    )

    return {
        "year": year,
        "has_data": True,
        "company_count": int(companies["company_id"].nunique()),
        "companies_with_ratio_data": int(ratios_year["company_id"].nunique()),
        "kpis": {
            "average_roe": float(avg_roe_winsorized) if pd.notna(avg_roe_winsorized) else None,
            "raw_average_roe": float(avg_roe_raw) if pd.notna(avg_roe_raw) else None,
            "median_pe": float(median_pe) if pd.notna(median_pe) else None,
            "median_de": float(median_de) if pd.notna(median_de) else None,
            "median_revenue_cagr_5yr": float(median_rev_cagr) if pd.notna(median_rev_cagr) else None,
            "debt_free_count": debt_free_count,
        },
        "sector_breakdown": sector_counts.to_dict(orient="records"),
        "top5": _sanitize_records(top5.to_dict(orient="records")),
    }


@router.get("/dashboard/capital-allocation")
def get_capital_allocation_dashboard(conn=Depends(get_db_connection)):
    """Return the latest cash-flow classification used by the treemap."""
    cf = pd.read_sql_query(
        """
        SELECT company_id, year, operating_activity, investing_activity, financing_activity
        FROM cashflow
        WHERE (company_id, year) IN (
            SELECT company_id, MAX(year) FROM cashflow GROUP BY company_id
        )
        """,
        conn,
    )
    pnl = pd.read_sql_query("SELECT company_id, year, net_profit FROM profitandloss", conn)
    companies = pd.read_sql_query("SELECT id AS company_id, company_name FROM companies", conn)
    sectors = pd.read_sql_query("SELECT company_id, broad_sector FROM sectors", conn)

    merged = cf.merge(pnl, on=["company_id", "year"], how="left")
    merged["cfo_pat_ratio"] = merged["operating_activity"] / merged["net_profit"].replace(0, float("nan"))

    merged["pattern_label"] = merged.apply(
        lambda row: classify_capital_allocation(
            row["operating_activity"],
            row["investing_activity"],
            row["financing_activity"],
            cfo_pat_ratio=(row["cfo_pat_ratio"] if pd.notna(row["cfo_pat_ratio"]) else None),
        ),
        axis=1,
    )
    merged = merged.merge(companies, on="company_id", how="left").merge(sectors, on="company_id", how="left")

    columns = ["company_id", "company_name", "broad_sector", "year", "pattern_label"]
    return {
        "count": len(merged),
        "companies": _sanitize_records(merged[columns].to_dict(orient="records")),
    }