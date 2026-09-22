"""Peer Comparison screen: API-backed radar chart and benchmark-highlighted table."""

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils.api_client import APIClientError, get_peer_group, get_peer_group_names

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "analytics"))
from radar_charts import RADAR_AXES, RAW_METRIC_MAP  # type: ignore

st.set_page_config(layout="wide")

st.title("Peer Comparison")

try:
    groups = get_peer_group_names()
except APIClientError as exc:
    st.error(str(exc))
    st.stop()

if not groups:
    st.warning("No peer groups found in the backend.")
    st.stop()

group_name = st.selectbox(
    "Peer group",
    groups,
    index=None,
    placeholder="Select a peer group…",
)
if group_name is None:
    st.info("Select a peer group to load the peer comparison.")
    st.stop()

try:
    payload = get_peer_group(group_name)
except APIClientError as exc:
    st.error(str(exc))
    st.stop()

rows = []
for company in payload["companies"]:
    row = {
        "company_id": company["company_id"],
        "company_name": company.get("company_name"),
        "is_benchmark": int(company.get("is_benchmark", False)),
    }
    row.update(company.get("latest_kpis") or {})
    for metric, metric_data in (company.get("metrics") or {}).items():
        row[metric] = metric_data.get("value")
    rows.append(row)

group_df = pd.DataFrame(rows)
if group_df.empty:
    st.warning(f"No peer data available for '{group_name}'.")
    st.stop()

# Scale the 8 radar metrics 0-100 with the same winsorize+scale pipeline
# as Day 19's radar_charts.py, so this matches the already-generated PNGs.
scaled = group_df.copy()
for raw_col in RAW_METRIC_MAP.values():
    invert = raw_col == "debt_to_equity"
    if raw_col in scaled.columns:
        series = scaled[raw_col].copy()
        valid = series.dropna()
        if valid.empty or valid.min() == valid.max():
            scaled[raw_col + "_scaled"] = 50.0 if not valid.empty else 0.0
        else:
            clipped = valid.clip(valid.quantile(0.10), valid.quantile(0.90))
            min_val, max_val = clipped.min(), clipped.max()
            transformed = (clipped - min_val) / (max_val - min_val) * 100
            if invert:
                transformed = 100 - transformed
            scaled[raw_col + "_scaled"] = transformed.reindex(series.index).fillna(0)
    else:
        scaled[raw_col + "_scaled"] = 0.0

fcf = scaled["free_cash_flow_cr"] if "free_cash_flow_cr" in scaled.columns else pd.Series(dtype=float)
if fcf.dropna().empty or fcf.dropna().min() == fcf.dropna().max():
    scaled["free_cash_flow_cr_scaled"] = 50.0 if not fcf.dropna().empty else 0.0
else:
    valid = fcf.dropna()
    clipped = valid.clip(valid.quantile(0.10), valid.quantile(0.90))
    scaled_fcf = (clipped - clipped.min()) / (clipped.max() - clipped.min()) * 100
    scaled["free_cash_flow_cr_scaled"] = scaled_fcf.reindex(fcf.index).fillna(0)


def get_radar_values(row):
    """Get the eight display values for one company."""
    values = []
    for axis in RADAR_AXES:
        if axis == "FCF Score":
            values.append(float(row.get("free_cash_flow_cr_scaled", 0) or 0))
        elif axis == "Composite Score":
            values.append(float(row.get("composite_quality_score", 0) or 0))
        else:
            values.append(float(row.get(RAW_METRIC_MAP[axis] + "_scaled", 0) or 0))
    return values

axis_columns = [
    "free_cash_flow_cr_scaled" if axis == "FCF Score" else "composite_quality_score" if axis == "Composite Score" else RAW_METRIC_MAP[axis] + "_scaled"
    for axis in RADAR_AXES
]
peer_avg_values = [float(scaled[col].mean()) if pd.notna(scaled[col].mean()) else 0 for col in axis_columns]

company_options = (scaled["company_id"] + " — " + scaled["company_name"].fillna("")).tolist()
picked = st.selectbox(
    "Company",
    company_options,
    index=None,
    placeholder="Select a company…",
)
if picked is None:
    st.info("Select a company to compare it with the peer-group average.")
    st.stop()
picked_id = picked.split(" — ")[0]
company_row = scaled[scaled["company_id"] == picked_id].iloc[0]
company_values = get_radar_values(company_row)

fig = go.Figure()
fig.add_trace(
    go.Scatterpolar(
        r=company_values + company_values[:1],
        theta=RADAR_AXES + RADAR_AXES[:1],
        fill="toself",
        name=picked_id,
    )
)
fig.add_trace(
    go.Scatterpolar(
        r=peer_avg_values + peer_avg_values[:1],
        theta=RADAR_AXES + RADAR_AXES[:1],
        fill="none",
        name="Peer Group Avg",
        line={"dash": "dash"},
    )
)
fig.update_layout(
    polar={"radialaxis": {"visible": True, "range": [0, 100]}},
    showlegend=True,
    height=500,
    margin={"t": 30, "b": 30},
)
st.plotly_chart(fig, width="stretch")
st.caption(
    "All 8 axes are based on the stored peer dataset and normalized for the radar display. "
    "ROCE uses each company's single latest-snapshot value because no year-by-year ROCE history exists."
)

st.divider()
st.subheader(f"{group_name} — all members")

table_cols = [
    "company_id",
    "company_name",
    "is_benchmark",
    "composite_quality_score",
    "return_on_equity_pct",
    "roce_percentage",
    "net_profit_margin_pct",
    "debt_to_equity",
    "free_cash_flow_cr",
    "pat_cagr_5yr",
    "revenue_cagr_5yr",
]
table_cols = [c for c in table_cols if c in group_df.columns]
kpi_table = group_df[table_cols].sort_values("is_benchmark", ascending=False)


def highlight_benchmark(row):
    """Use the theme-aligned benchmark highlight from the UI pass."""
    if row["is_benchmark"] == 1:
        return [
            (
                "background-color: #123B43; color: #E6EDF2; font-weight: 600; "
                "border-top: 1px solid #00D2C4; border-bottom: 1px solid rgba(0, 210, 196, 0.35);"
            )
            for _ in row
        ]
    return [""] * len(row)


st.dataframe(kpi_table.style.apply(highlight_benchmark, axis=1), hide_index=True, width="stretch")