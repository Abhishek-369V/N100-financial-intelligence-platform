"""Capital Allocation Map: API-backed latest-year cash-flow classification treemap."""

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils.api_client import APIClientError, get_capital_allocation

st.set_page_config(layout="wide")

st.title("Capital Allocation Map")

try:
    payload = get_capital_allocation()
except APIClientError as exc:
    st.error(str(exc))
    st.stop()

merged = pd.DataFrame(payload["companies"])
if merged.empty:
    st.warning("No capital-allocation data found in the backend.")
    st.stop()

if len(merged) < 92:
    st.caption(f"{len(merged)} of 92 companies have a latest-year cashflow row to classify.")

# Keep the treemap aligned with the app's Deep Navy / Teal visual system.
# Distinct patterns remain easy to tell apart without the bright default Plotly palette.
PATTERN_COLORS = {
    "Reinvestor": "#00D2C4",
    "Shareholder Returns": "#3B82F6",
    "Growth Funded by Debt": "#F59E0B",
    "Distress Signal": "#EF4444",
    "Liquidating Assets": "#8B5CF6",
    "Mixed": "#64748B",
    "Pre-Revenue": "#A78BFA",
    "Cash Accumulator": "#22C55E",
    "Unclassified": "#475569",
}

fig = px.treemap(
    merged,
    path=["pattern_label", "company_id"],
    values=[1] * len(merged),
    color="pattern_label",
    color_discrete_map=PATTERN_COLORS,
)
fig.update_traces(marker_line_color="#07111F", marker_line_width=1.5)
fig.update_layout(height=550, margin={"t": 20, "b": 20})

event = st.plotly_chart(fig, width="stretch", on_select="rerun", selection_mode="points")

st.divider()

clicked_pattern = None
if event and event.selection and event.selection.points:
    point = event.selection.points[0]
    # Treemap click gives the full path label; top-level pattern clicks
    # land directly on a pattern name, company-level clicks land on a
    # company_id -- resolve either back to its pattern.
    label = point.get("label")
    if label in merged["pattern_label"].values:
        clicked_pattern = label
    elif label in merged["company_id"].values:
        clicked_pattern = merged.loc[merged["company_id"] == label, "pattern_label"].iloc[0]

if clicked_pattern:
    st.subheader(f"Companies classified as: {clicked_pattern}")
    subset = merged[merged["pattern_label"] == clicked_pattern][
        ["company_id", "company_name", "broad_sector"]
    ]
    st.dataframe(subset, hide_index=True, width="stretch")
else:
    st.caption("Click a pattern (or a company within it) in the treemap above to see the full list.")