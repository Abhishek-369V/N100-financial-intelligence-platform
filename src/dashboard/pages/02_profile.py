"""Company Profile: company metadata, KPI history, P&L trend and pros/cons."""

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils.api_client import APIClientError, get_companies, get_company_pl, get_company_profile, get_company_ratios

st.set_page_config(layout="wide")

st.title("Company Profile")

try:
    companies_payload = get_companies()
except APIClientError as exc:
    st.error(str(exc))
    st.stop()

companies = pd.DataFrame(companies_payload["companies"])
if companies.empty:
    st.warning("No companies found in the backend.")
    st.stop()

options = (companies["id"] + " — " + companies["company_name"]).sort_values().tolist()
picked = st.selectbox(
    "Search company name or ticker",
    options,
    index=None,
    placeholder="Start typing a company name or ticker…",
)
if picked is None:
    st.info("Select a company to load its profile and financial history.")
    st.stop()
ticker = picked.split(" — ")[0]

try:
    profile_payload = get_company_profile(ticker)
    ratios = pd.DataFrame(get_company_ratios(ticker)["ratios"])
    pl = pd.DataFrame(get_company_pl(ticker)["profit_and_loss"])
except APIClientError as exc:
    st.error(str(exc))
    st.stop()

row = profile_payload["company"]
sector = profile_payload.get("sector") or {}
latest = profile_payload.get("latest_year_kpis")

st.subheader(row["company_name"])
c1, c2, c3 = st.columns(3)
c1.write(f"**Sector:** {sector.get('broad_sector', 'N/A')}")
c2.write(f"**Sub-sector:** {sector.get('sub_sector', 'N/A')}")
c3.write(f"**NSE Ticker:** {ticker}")
desc = row.get("about_company") or "_No description available._"
st.write(f"**Description:** {desc}")

st.divider()

k1, k2, k3, k4, k5, k6 = st.columns(6)
if latest is not None:
    k1.metric("ROE", f"{latest['return_on_equity_pct']:.1f}%")
    k2.metric(
        "ROCE (latest snapshot)",
        f"{row['roce_percentage']:.1f}%" if pd.notna(row.get("roce_percentage")) else "N/A",
    )
    k3.metric("Net Profit Margin", f"{latest['net_profit_margin_pct']:.1f}%")
    k4.metric("D/E", f"{latest['debt_to_equity']:.2f}")
    k5.metric(
        "Revenue CAGR 5yr",
        f"{latest['revenue_cagr_5yr']:.1f}%" if pd.notna(latest["revenue_cagr_5yr"]) else "N/A",
    )
    k6.metric(
        "FCF (latest yr, Cr)",
        f"{latest['free_cash_flow_cr']:.0f}" if pd.notna(latest["free_cash_flow_cr"]) else "N/A",
    )
else:
    st.info("No financial_ratios data available for this company.")

st.divider()

if not pl.empty:
    st.subheader("Revenue & Net Profit")
    pl = pl.sort_values("year").tail(10)
    fig = go.Figure()
    fig.add_bar(x=pl["year"], y=pl["sales"], name="Revenue (₹ Cr)", hovertemplate="₹%{y:,.0f} Cr<extra>Revenue</extra>")
    fig.add_bar(x=pl["year"], y=pl["net_profit"], name="Net Profit (₹ Cr)", hovertemplate="₹%{y:,.0f} Cr<extra>Net Profit</extra>")
    fig.update_layout(barmode="group", height=380, margin={"t": 10, "b": 10})
    st.plotly_chart(fig, width="stretch")
    if len(pl) < 10:
        st.caption(f"Only {len(pl)} years of P&L data available for this company.")
else:
    st.info("No profit & loss history available.")

if not ratios.empty:
    ratios = ratios.sort_values("year")
    st.subheader("ROE vs ROCE")
    roe_hist = ratios.tail(10)
    fig2 = make_subplots(specs=[[{"secondary_y": True}]])
    fig2.add_trace(
        go.Scatter(
            x=roe_hist["year"],
            y=roe_hist["return_on_equity_pct"],
            name="ROE %",
            mode="lines+markers",
            hovertemplate="ROE: %{y:.1f}%<extra></extra>",
        ),
        secondary_y=False,
    )
    if pd.notna(row.get("roce_percentage")):
        fig2.add_hline(
            y=row["roce_percentage"],
            line_dash="dot",
            annotation_text=f"ROCE (latest snapshot, static): {row['roce_percentage']:.1f}%",
            secondary_y=True,
        )
    fig2.update_layout(height=360, margin={"t": 10, "b": 10})
    st.plotly_chart(fig2, width="stretch")
    st.caption(
        "ROCE has no year-by-year history in the database (only a single latest-snapshot value "
        "in the companies table) — shown as a flat reference line rather than a fabricated trend."
    )

pc = profile_payload.get("pros_cons")
st.subheader("Pros & Cons")
if not pc or (not pc.get("pros") and not pc.get("cons")):
    st.caption("No pros/cons data available for this company in the source file.")
else:
    pros_items = [p.strip() for p in (pc.get("pros") or "").split(". ") if p.strip()]
    cons_items = [c.strip() for c in (pc.get("cons") or "").split(". ") if c.strip()]
    pcol, ccol = st.columns(2)
    with pcol:
        for item in pros_items:
            st.success(f"✅ {item}")
    with ccol:
        for item in cons_items:
            st.error(f"❌ {item}")