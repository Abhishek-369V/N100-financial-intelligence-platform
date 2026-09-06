"""Day 23 — Home screen: KPI tiles, sector donut, top-5 table, year selector."""
import sys
from pathlib import Path
import streamlit as st
import plotly.graph_objects as go
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils.db import get_ratios, get_companies, get_sectors, db_engine

# Reuse Sprint 3's own winsorize + composite-score engine — no new formula code, same logic already used/verified for the screener.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "screener"))
from composite_score import winsorize, compute_composite_score #type:ignore
from engine import load_universe #type:ignore

# Force wide mode configuration to ensure - No UI break - 6 metrics stay side-by-side
st.set_page_config(layout="wide")

st.title("Home")

YEARS = [2019, 2020, 2021, 2022, 2023, 2024]
selected_year = st.sidebar.selectbox("Year", YEARS, index=len(YEARS) - 1)

ratios_all = get_ratios()
companies = get_companies()
sectors = get_sectors()

# financial_ratios.year is 'YYYY-MM' (fiscal year-end varies by company - documented Sprint 2 finding). 
# Filter to the selected calendar year, then take the latest month-end available per company within that year 
# so every company contributes at most one row.
ratios_all["calendar_year"] = ratios_all["year"].str[:4].astype(int)
ratios_year = (
    ratios_all[ratios_all["calendar_year"] == selected_year]
    .sort_values("year")
    .groupby("company_id")
    .last()
    .reset_index()
)

if ratios_year.empty:
    st.warning(f"No financial_ratios data found for {selected_year}.")
else:
    n_with_data = ratios_year["company_id"].nunique()
    if n_with_data < companies["company_id"].nunique():
        st.caption(
            f"Note: {n_with_data} of {companies['company_id'].nunique()} companies have a financial_ratios row for {selected_year}."
        )

    # Winsorized (P10/P90 capped) average ROE — display-only fix for known data-entry outliers (BEL/INDIGO-style).
    # Underlying financial_ratios data is untouched; only this KPI's calculation clips the extremes before averaging. 
    avg_roe_raw = ratios_year["return_on_equity_pct"].mean()
    avg_roe_winsorized = winsorize(ratios_year["return_on_equity_pct"]).mean()

    debt_free_count = (ratios_year["debt_to_equity"] == 0).sum()
    median_de = ratios_year["debt_to_equity"].median()
    median_rev_cagr = ratios_year["revenue_cagr_5yr"].median()

    mc = pd.read_sql(
        "SELECT company_id, pe_ratio FROM market_cap WHERE year = :y",
        db_engine, params={"y": f"{selected_year}-03"},
    )
    median_pe = mc["pe_ratio"].median() if not mc.empty else None

    col1, col2, col3, col4, col5, col6 = st.columns(6)
    col1.metric("Average ROE", f"{avg_roe_winsorized:.1f}%" if avg_roe_winsorized is not None else "N/A")
    col2.metric("Median P/E", f"{median_pe:.1f}" if median_pe is not None else "N/A")
    col3.metric("Median D/E", f"{median_de:.2f}" if median_de is not None else "N/A")
    col4.metric("Total Companies", companies["company_id"].nunique())
    col5.metric("Median Revenue CAGR 5yr", f"{median_rev_cagr:.1f}%" if median_rev_cagr is not None else "N/A")
    col6.metric("Debt-Free Companies", int(debt_free_count))

    st.caption(f"Raw (non-winsorized) average ROE for {selected_year} was {avg_roe_raw:.1f}% "
               f"— capped to {avg_roe_winsorized:.1f}% at the 10th/90th percentile.")

    st.divider()
    left, right = st.columns([1, 1])

    with left:
        st.subheader("Sector Breakdown")
        sector_counts = sectors["broad_sector"].value_counts().reset_index()
        sector_counts.columns = ["broad_sector", "count"]
        fig = go.Figure(data=[go.Pie(
            labels=sector_counts["broad_sector"], values=sector_counts["count"], hole=0.5,
        )])
        fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=380)
        st.plotly_chart(fig, width="stretch")
        st.caption(
            f"{sector_counts.shape[0]} sectors, {sector_counts['count'].sum()} companies. "
            f"Note: spec references 11 sectors; the sectors table only has "
            f"{sector_counts.shape[0]} distinct broad_sector values — flagging "
            f"the mismatch rather than inventing an 11th."
        )

    with right:
        st.subheader("Top 5 — Composite Quality Score")

        universe = load_universe()
        universe = universe.merge(
            pd.read_sql("SELECT id AS company_id, roce_percentage FROM companies", db_engine),
            on="company_id", how="left",
        )
        scored = compute_composite_score(universe, sector_relative=False)
        top5 = (
            scored.merge(companies[["company_id", "company_name"]], on="company_id", how="left")
            .sort_values("composite_quality_score", ascending=False)
            .head(5)[["company_id", "company_name", "composite_quality_score"]]
        )
        st.dataframe(
            top5, 
            hide_index=True, 
            width="stretch",
            column_config={
                "company_id": st.column_config.TextColumn("Company ID", width="stretch"),
                "company_name": st.column_config.TextColumn("Company Name", width="stretch"),
                "composite_quality_score": st.column_config.NumberColumn("Score", width="stretch", format="%.2f")
            }
        )
        
        st.caption(
            "Composite score is always based on each company's latest available "
            "data — it can't be recomputed for an arbitrary past year with the "
            "current engine (FCF CAGR is hardwired to the latest 5 years in "
            "cashflow_kpis' CAGR window), so this table doesn't change with the "
            "year selector. That's a real infra limitation, not a display bug."
        )