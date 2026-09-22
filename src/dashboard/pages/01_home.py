"""Home dashboard: portfolio KPIs, sector mix and top composite scores."""

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# add FastAPI client as backend and Removed linkage between sqlite.db 
from utils.api_client import APIClientError, get_home 

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

st.set_page_config(layout="wide")

st.markdown(
    """
    <div class="n100-home-hero">
        <div class="n100-home-eyebrow">N100 FINANCIAL INTELLIGENCE</div>
        <h1>NIFTY 100 Financial Intelligence</h1>
        <p>Financial analytics &amp; research workspace</p>
        <div class="n100-home-status">92 companies &nbsp;·&nbsp; 30+ KPIs &nbsp;·&nbsp; 8 analytical screens</div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <style>
        .n100-home-hero {
            padding: 0.35rem 0 0.9rem 0;
            margin-bottom: 0.5rem;
            border-bottom: 1px solid rgba(148, 163, 184, 0.16);
        }
        .n100-home-eyebrow {
            color: #00D2C4;
            font-size: 0.72rem;
            font-weight: 700;
            letter-spacing: 0.12em;
            margin-bottom: 0.25rem;
        }
        .n100-home-hero h1 {
            color: #E6EDF2;
            font-size: 2rem;
            line-height: 1.15;
            margin: 0;
            letter-spacing: -0.03em;
        }
        .n100-home-hero p {
            color: #A0AEC0;
            font-size: 0.95rem;
            margin: 0.35rem 0 0 0;
        }
        .n100-home-status {
            color: #94A3B8;
            font-size: 0.76rem;
            margin-top: 0.55rem;
            letter-spacing: 0.03em;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

YEARS = [2019, 2020, 2021, 2022, 2023, 2024]
selected_year = st.sidebar.selectbox("Year", YEARS, index=len(YEARS) - 1)

try:
    payload = get_home(selected_year)
except APIClientError as exc:
    st.error(str(exc))
    st.stop()

if not payload.get("has_data"):
    st.warning(f"No financial_ratios data found for {selected_year}.")
    st.stop()

company_count = payload["company_count"]
companies_with_data = payload["companies_with_ratio_data"]
if companies_with_data < company_count:
    st.caption(f"Note: {companies_with_data} of {company_count} companies have a financial_ratios row for {selected_year}.")

kpis = payload["kpis"]
col1, col2, col3, col4, col5, col6 = st.columns(6)
col1.metric("Average ROE", f"{kpis['average_roe']:.1f}%" if kpis["average_roe"] is not None else "N/A")
col2.metric("Median P/E", f"{kpis['median_pe']:.1f}" if kpis["median_pe"] is not None else "N/A")
col3.metric("Median D/E", f"{kpis['median_de']:.2f}" if kpis["median_de"] is not None else "N/A")
col4.metric("Total Companies", company_count)
col5.metric(
    "Median Revenue CAGR 5yr",
    f"{kpis['median_revenue_cagr_5yr']:.1f}%" if kpis["median_revenue_cagr_5yr"] is not None else "N/A",
)
col6.metric("Debt-Free Companies", int(kpis["debt_free_count"]))

if kpis["raw_average_roe"] is not None and kpis["average_roe"] is not None:
    st.caption(
        f"Raw (non-winsorized) average ROE for {selected_year} was {kpis['raw_average_roe']:.1f}% "
        f"— capped to {kpis['average_roe']:.1f}% at the 10th/90th percentile."
    )

st.divider()
left, right = st.columns([1, 1])

with left:
    st.subheader("Sector Breakdown")
    sector_df = pd.DataFrame(payload["sector_breakdown"])
    fig = go.Figure(
        data=[
            go.Pie(
                labels=sector_df["broad_sector"],
                values=sector_df["count"],
                hole=0.5,
            )
        ]
    )
    fig.update_layout(margin={"t": 10, "b": 10, "l": 10, "r": 10}, height=380)
    st.plotly_chart(fig, width="stretch")
    st.caption(
        f"{len(sector_df)} sectors, {sector_df['count'].sum()} companies. "
        "The backend returns the live sector inventory from the database."
    )

with right:
    st.subheader("Top 5 — Composite Quality Score")
    top5 = pd.DataFrame(payload["top5"])
    st.dataframe(
        top5,
        hide_index=True,
        width="stretch",
        column_config={
            "company_id": st.column_config.TextColumn("Company ID", width="stretch"),
            "company_name": st.column_config.TextColumn("Company Name", width="stretch"),
            "composite_quality_score": st.column_config.NumberColumn("Score", width="stretch", format="%.2f"),
        },
    )
    st.caption(
        "Composite score is based on each company's latest available data, "
        "so this table does not change with the year selector."
    )