"""Day 25 — Sector Analysis: bubble chart + sector median KPI bars."""
import sys
from pathlib import Path
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils.db import get_sectors, get_ratios, db_engine

st.set_page_config(layout="wide")

st.title("Sector Analysis")

sectors = get_sectors()
if sectors.empty:
    st.warning("No sector data found.")
    st.stop()

broad_sector = st.selectbox("Sector", sorted(sectors["broad_sector"].dropna().unique()))

# Latest-year snapshot per company: 
# revenue (profitandloss), ROE(financial_ratios), market cap (market_cap) 
# -- three different source tables, each joined on its own latest year per company.
pnl_latest = pd.read_sql(
    "SELECT company_id, sales FROM profitandloss "
    "WHERE (company_id, year) IN (SELECT company_id, MAX(year) FROM profitandloss GROUP BY company_id)",
    db_engine,
)
mc_latest = pd.read_sql(
    "SELECT company_id, market_cap_crore FROM market_cap "
    "WHERE (company_id, year) IN (SELECT company_id, MAX(year) FROM market_cap GROUP BY company_id)",
    db_engine,
)
ratios_latest = get_ratios().sort_values("year").groupby("company_id").last().reset_index()
companies_names = pd.read_sql("SELECT id AS company_id, company_name FROM companies", db_engine)

sector_companies = sectors[sectors["broad_sector"] == broad_sector]

merged = (
    sector_companies
    .merge(pnl_latest, on="company_id", how="left")
    .merge(mc_latest, on="company_id", how="left")
    .merge(ratios_latest[["company_id", "return_on_equity_pct"]], on="company_id", how="left")
    .merge(companies_names, on="company_id", how="left")
)
merged = merged.dropna(subset=["sales", "return_on_equity_pct", "market_cap_crore"])

if merged.empty:
    st.warning(f"No complete revenue/ROE/market-cap data for any company in {broad_sector}.")
else:
    st.subheader(f"{broad_sector} — Revenue vs ROE (bubble = market cap)")
    fig = px.scatter(
        merged, x="sales", y="return_on_equity_pct", size="market_cap_crore",
        color="sub_sector", hover_name="company_name",
        labels={"sales": "Revenue (₹ Cr)", "return_on_equity_pct": "ROE (%)", "sub_sector": "Sub-sector"},
        size_max=50,
    )
    fig.update_layout(height=480, margin=dict(t=20, b=20))
    st.plotly_chart(fig, width="stretch")
    if len(merged) < len(sector_companies):
        st.caption(f"{len(merged)} of {len(sector_companies)} companies in {broad_sector} "
                   f"have complete revenue/ROE/market-cap data to plot.")

    st.divider()
    st.subheader(f"{broad_sector} — Median KPIs")
    median_metrics = {
        "Median ROE (%)": merged["return_on_equity_pct"].median(),
        "Median Revenue (₹ Cr)": merged["sales"].median(),
        "Median Market Cap (₹ Cr)": merged["market_cap_crore"].median(),
    }
    bar_fig = go.Figure(go.Bar(
                            x=list(
                                median_metrics.keys()), 
                                y=list(median_metrics.values())
                            )
                        )
    bar_fig.update_layout(height=350, margin=dict(t=20, b=20))
    st.plotly_chart(bar_fig, width="stretch")