"""Day 23 — Company Profile screen: search, card, KPI tiles, charts, pros/cons."""
import sys
from pathlib import Path
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils.db import get_companies, get_ratios, get_pl, db_engine

st.set_page_config(layout="wide")

st.title("Company Profile")

companies = get_companies()

options = (companies["company_id"] + " — " + companies["company_name"]).sort_values().tolist()
picked = st.selectbox("Search company name or ticker", options, index=None, placeholder="Start typing…")

ticker = picked.split(" — ")[0] if picked else None

if picked is None:
    st.caption("Type a company name or ticker to search.")
elif ticker not in companies["company_id"].values:
    st.warning("Ticker not found — please try another")

if ticker:
    row = companies[companies["company_id"] == ticker].iloc[0]

    st.subheader(row["company_name"])
    c1, c2, c3 = st.columns(3)
    c1.write(f"**Sector:** {row['broad_sector']}")
    c2.write(f"**Sub-sector:** {row['sub_sector']}")
    c3.write(f"**NSE Ticker:** {ticker}")
    desc = row['about_company'] or "_No description available._"
    st.write(f"**Description:** {desc}")


    st.divider()

    ratios_hist = get_ratios(ticker).sort_values("year")
    latest = ratios_hist.iloc[-1] if not ratios_hist.empty else None

    k1, k2, k3, k4, k5, k6 = st.columns(6)
    if latest is not None:
        k1.metric("ROE", f"{latest['return_on_equity_pct']:.1f}%")
        # ROCE has no per-year history in financial_ratios — it's a single
        # static snapshot value in the companies table, not a time series.
        k2.metric("ROCE (latest snapshot)", f"{row['roce_percentage']:.1f}%" if pd.notna(row["roce_percentage"]) else "N/A")
        k3.metric("Net Profit Margin", f"{latest['net_profit_margin_pct']:.1f}%")
        k4.metric("D/E", f"{latest['debt_to_equity']:.2f}")
        k5.metric("Revenue CAGR 5yr", f"{latest['revenue_cagr_5yr']:.1f}%" if pd.notna(latest["revenue_cagr_5yr"]) else "N/A")
        k6.metric("FCF (latest yr, Cr)", f"{latest['free_cash_flow_cr']:.0f}" if pd.notna(latest["free_cash_flow_cr"]) else "N/A")
    else:
        st.info("No financial_ratios data available for this company.")

    st.divider()

    pl = get_pl(ticker).sort_values("year").tail(10)
    if not pl.empty:
        st.subheader("Revenue & Net Profit")
        fig = go.Figure()
        fig.add_bar(
            x=pl["year"], 
            y=pl["sales"], 
            name="Revenue (₹ Cr)",
            hovertemplate="₹%{y:,.0f} Cr<extra>Revenue</extra>"
        )
        fig.add_bar(
            x=pl["year"], 
            y=pl["net_profit"], 
            name="Net Profit (₹ Cr)",
            hovertemplate="₹%{y:,.0f} Cr<extra>Net Profit</extra>"
        )
        fig.update_layout(barmode="group", height=380, margin=dict(t=10, b=10))
        st.plotly_chart(fig, width="stretch")
        if len(pl) < 10:
            st.caption(f"Only {len(pl)} years of P&L data available for this company.")
    else:
        st.info("No profit & loss history available.")

    if not ratios_hist.empty:
        st.subheader("ROE vs ROCE")
        roe_hist = ratios_hist.tail(10)
        fig2 = make_subplots(specs=[[{"secondary_y": True}]])
        fig2.add_trace(
            go.Scatter(
                x=roe_hist["year"], 
                y=roe_hist["return_on_equity_pct"], 
                name="ROE %", 
                mode="lines+markers",
                hovertemplate="ROE: %{y:.1f}%<extra></extra>"
            ),
            secondary_y=False,
        )
        if pd.notna(row["roce_percentage"]):
            fig2.add_hline(
                y=row["roce_percentage"], line_dash="dot",
                annotation_text=f"ROCE (latest snapshot, static): {row['roce_percentage']:.1f}%", secondary_y=True,
            )
        fig2.update_layout(height=360, margin=dict(t=10, b=10))
        st.plotly_chart(fig2, width="stretch")
        st.caption(
            "ROCE has no year-by-year history in the database (only a single "
            "latest-snapshot value in the companies table) — shown as a flat "
            "reference line rather than a fabricated trend."
        )

    pc = pd.read_sql(
        "SELECT pros, cons FROM prosandcons WHERE company_id = :t", db_engine, params={"t": ticker}
    )
    st.subheader("Pros & Cons")
    if pc.empty or (not pc.iloc[0]["pros"] and not pc.iloc[0]["cons"]):
        # prosandcons only has 14 rows total covering 92 companies -- sparse
        # source coverage (same pattern as peer_groups.xlsx only covering 56/92).
        st.caption("No pros/cons data available for this company in the source file.")
    else:
        pros_items = [p.strip() for p in (pc.iloc[0]["pros"] or "").split(". ") if p.strip()]
        cons_items = [c.strip() for c in (pc.iloc[0]["cons"] or "").split(". ") if c.strip()]
        pcol, ccol = st.columns(2)
        with pcol:
            for p in pros_items:
                st.success(f"✅ {p}")
        with ccol:
            for c in cons_items:
                st.error(f"❌ {c}")