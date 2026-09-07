"""Day 24 — Peer Comparison screen: radar chart + benchmark-highlighted KPI table."""
import sys
from pathlib import Path
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils.db import get_peer_group_names, db_engine

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "screener"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "analytics"))
from engine import load_universe #type:ignore
from composite_score import compute_composite_score, winsorize, scale_0_100 #type:ignore
from radar_charts import RADAR_AXES, RAW_METRIC_MAP  # reuse Day 19's exact 8 axes #type:ignore

st.title("Peer Comparison")

groups = get_peer_group_names()
if not groups:
    st.warning("No peer groups found in the database.")
    st.stop()

group_name = st.selectbox("Peer group", groups)

members = pd.read_sql(
    "SELECT company_id, is_benchmark FROM peer_groups WHERE peer_group_name = :g",
    db_engine, params={"g": group_name},
)

universe = load_universe()
extra = pd.read_sql(
    "SELECT id AS company_id, company_name, roce_percentage FROM companies", db_engine
)
universe = universe.merge(extra, on="company_id", how="left")
scored = compute_composite_score(universe, sector_relative=False)

group_df = scored.merge(members, on="company_id", how="inner")

if group_df.empty:
    st.warning(f"No scored data available for '{group_name}'.")
    st.stop()

# Scale the 8 radar metrics 0-100 with the same winsorize+scale pipeline
# as Day 19's radar_charts.py, so this matches the already-generated PNGs.
scaled = group_df.copy()
for axis, raw_col in RAW_METRIC_MAP.items():
    invert = raw_col == "debt_to_equity"
    if raw_col in scaled.columns:
        scaled[raw_col + "_scaled"] = scale_0_100(winsorize(scaled[raw_col]), invert=invert)
    else:
        scaled[raw_col + "_scaled"] = None
scaled["free_cash_flow_cr_scaled"] = scale_0_100(winsorize(scaled["free_cash_flow_cr"]))

def get_radar_values(row):
    values = []
    for axis in RADAR_AXES:
        if axis == "FCF Score":
            values.append(row.get("free_cash_flow_cr_scaled") or 0)
        elif axis == "Composite Score":
            values.append(row.get("composite_quality_score") or 0)
        else:
            values.append(row.get(RAW_METRIC_MAP[axis] + "_scaled") or 0)
    return values

peer_avg_values = [scaled[c].mean() for c in
                    [("free_cash_flow_cr_scaled" if a == "FCF Score" else
                      "composite_quality_score" if a == "Composite Score" else
                      RAW_METRIC_MAP[a] + "_scaled") for a in RADAR_AXES]]
peer_avg_values = [v if pd.notna(v) else 0 for v in peer_avg_values]

company_options = (scaled["company_id"] + " — " + scaled["company_name"].fillna("")).tolist()
picked = st.selectbox("Company", company_options)
picked_id = picked.split(" — ")[0]
company_row = scaled[scaled["company_id"] == picked_id].iloc[0]
company_values = get_radar_values(company_row)

fig = go.Figure()
fig.add_trace(go.Scatterpolar(
    r=company_values + company_values[:1], 
    theta=RADAR_AXES + RADAR_AXES[:1],
    fill="toself", name=picked_id,
))
fig.add_trace(go.Scatterpolar(
    r=peer_avg_values + peer_avg_values[:1], 
    theta=RADAR_AXES + RADAR_AXES[:1],
    fill="none", 
    name="Peer Group Avg", 
    line=dict(dash="dash"),
))
fig.update_layout(
    polar=dict(
        radialaxis=dict(visible=True, range=[0, 100])),
        showlegend=True, 
        height=500, 
        margin=dict(t=30, b=30),
)
st.plotly_chart(fig, use_container_width=True)
st.caption(
    "All 8 axes are winsorized + scaled 0-100 (same pipeline as Day 19's static "
    "radar PNGs). ROCE uses each company's single latest-snapshot value (no "
    "year-by-year history exists) — same caveat as the Company Profile screen."
)

st.divider()
st.subheader(f"{group_name} — all members")

table_cols = [
    "company_id", "company_name", "is_benchmark", "composite_quality_score",
    "return_on_equity_pct", "roce_percentage", "net_profit_margin_pct",
    "debt_to_equity", "free_cash_flow_cr", "pat_cagr_5yr", "revenue_cagr_5yr",
]
table_cols = [c for c in table_cols if c in group_df.columns]
kpi_table = group_df[table_cols].sort_values("is_benchmark", ascending=False)

def highlight_benchmark(row):
    return ["background-color: #FFD700" if row["is_benchmark"] == 1 else "" for _ in row]

st.dataframe(kpi_table.style.apply(highlight_benchmark, axis=1), hide_index=True, use_container_width=True)