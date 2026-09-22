"""Sector Analysis: API-backed revenue-vs-ROE bubble chart and medians."""

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils.api_client import APIClientError, get_sector_companies, get_sectors

st.set_page_config(layout="wide")

st.title("Sector Analysis")

try:
    sector_payload = get_sectors()
except APIClientError as exc:
    st.error(str(exc))
    st.stop()

sector_names = sorted(row["broad_sector"] for row in sector_payload["sectors"] if row.get("broad_sector"))
if not sector_names:
    st.warning("No sector data found in the backend.")
    st.stop()

broad_sector = st.selectbox("Sector", sector_names)

try:
    companies_payload = get_sector_companies(broad_sector)
except APIClientError as exc:
    st.error(str(exc))
    st.stop()

merged = pd.DataFrame(companies_payload["companies"])
merged = merged.dropna(subset=["sales", "return_on_equity_pct", "market_cap_crore"])

if merged.empty:
    st.warning(f"No complete revenue/ROE/market-cap data for any company in {broad_sector}.")
else:
    st.subheader(f"{broad_sector} — Revenue vs ROE (bubble = market cap)")
    fig = px.scatter(
        merged,
        x="sales",
        y="return_on_equity_pct",
        size="market_cap_crore",
        color="sub_sector",
        hover_name="company_name",
        labels={"sales": "Revenue (₹ Cr)", "return_on_equity_pct": "ROE (%)", "sub_sector": "Sub-sector"},
        size_max=50,
    )
    fig.update_layout(height=480, margin={"t": 20, "b": 20})
    st.plotly_chart(fig, width="stretch")

    total_in_sector = companies_payload["count"]
    if len(merged) < total_in_sector:
        st.caption(
            f"{len(merged)} of {total_in_sector} companies in {broad_sector} "
            "have complete revenue/ROE/market-cap data to plot."
        )

    st.divider()
    st.subheader(f"{broad_sector} — Median KPIs")
    median_metrics = {
        "Median ROE (%)": merged["return_on_equity_pct"].median(),
        "Median Revenue (₹ Cr)": merged["sales"].median(),
        "Median Market Cap (₹ Cr)": merged["market_cap_crore"].median(),
    }
    bar_fig = go.Figure(go.Bar(x=list(median_metrics.keys()), y=list(median_metrics.values())))
    bar_fig.update_layout(height=350, margin={"t": 20, "b": 20})
    st.plotly_chart(bar_fig, width="stretch")