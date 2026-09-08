"""Day 25 — Trend Analysis: company search + up-to-3-metric overlay, YoY annotations."""
import sys
from pathlib import Path
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils.db import get_companies, get_ratios, get_pl

st.set_page_config(layout="wide")

st.title("Trend Analysis")

companies = get_companies()
options = (companies["company_id"] + " — " + companies["company_name"]).sort_values().tolist()
picked = st.selectbox("Company", options, index=None, placeholder="Search company name or ticker…")

# Metrics grouped by unit, since overlaying % metrics with ₹ Cr metrics on
# one axis would make the ₹ Cr line dwarf everything else. % metrics share
# the primary axis, ₹ Cr metrics get the secondary axis.
PCT_METRICS = {
    "ROE (%)": "return_on_equity_pct",
    "Net Profit Margin (%)": "net_profit_margin_pct",
    "Operating Margin (%)": "operating_profit_margin_pct",
    "D/E": "debt_to_equity",
    "Revenue CAGR 5yr (%)": "revenue_cagr_5yr",
    "PAT CAGR 5yr (%)": "pat_cagr_5yr",
}
CR_METRICS = {
    "Revenue (₹ Cr)": "sales",
    "Net Profit (₹ Cr)": "net_profit",
    "Free Cash Flow (₹ Cr)": "free_cash_flow_cr",
}
ALL_METRICS = {**PCT_METRICS, **CR_METRICS}

selected = st.multiselect(
    "Metrics to overlay (up to 3)", 
    list(ALL_METRICS.keys()), 
    max_selections=3
)

if not picked:
    st.caption("Search a company and pick up to 3 metrics to see their 10-year trend.")
elif not selected:
    st.caption("Pick at least one metric.")
else:
    ticker = picked.split(" — ")[0]
    ratios = get_ratios(ticker).sort_values("year").tail(10)
    pl = get_pl(ticker).sort_values("year").tail(10)
    # ratios and pl may not share identical year sets 
    # (different source files) -- merge on year so every plotted point has a matching x-axis label
    merged = pd.merge(ratios, pl, on=["company_id", "year"], how="outer").sort_values("year")

    if len(merged) < 10:
        st.caption(f"Only {len(merged)} years of data available for this company.")

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    has_pct = any(m in PCT_METRICS for m in selected)
    has_cr = any(m in CR_METRICS for m in selected)

    for metric_label in selected:
        col = ALL_METRICS[metric_label]
        if col not in merged.columns:
            continue
        series = merged[["year", col]].dropna()
        yoy_pct = series[col].pct_change() * 100

        on_secondary = metric_label in CR_METRICS
        fig.add_trace(
            go.Scatter(
                x=series["year"], y=series[col], name=metric_label, mode="lines+markers+text",
                text=[f"{v:+.1f}% YoY" if pd.notna(v) else "" for v in yoy_pct],
                textposition="top center",
                hovertemplate="%{x}: %{y:,.1f}<br>%{text}<extra>" + metric_label + "</extra>",
            ),
            secondary_y=on_secondary,
        )

    fig.update_layout(height=460, margin=dict(t=30, b=30), hovermode="x unified")
    if has_pct:
        fig.update_yaxes(title_text="% / ratio", secondary_y=False)
    if has_cr:
        fig.update_yaxes(title_text="₹ Cr", secondary_y=True)

    st.plotly_chart(fig, width="stretch")
    st.caption("YoY % change is shown above each point and in its hover label. Metrics "
               "measured in % share the left axis; ₹ Cr metrics use the right axis.")