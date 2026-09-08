"""Day 25 — Capital Allocation Map: treemap of 92 companies by CFO/CFI/CFF pattern."""
import sys
from pathlib import Path
import streamlit as st
import pandas as pd
import plotly.express as px

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils.db import db_engine

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "analytics"))
from cashflow_kpis import classify_capital_allocation #type:ignore

st.set_page_config(layout="wide")

st.title("Capital Allocation Map")

cf_latest = pd.read_sql(
    "SELECT company_id, year, operating_activity, investing_activity, financing_activity FROM cashflow "
    "WHERE (company_id, year) IN (SELECT company_id, MAX(year) FROM cashflow GROUP BY company_id)",
    db_engine,
)
pnl = pd.read_sql("SELECT company_id, year, net_profit FROM profitandloss", db_engine)
companies = pd.read_sql("SELECT id AS company_id, company_name FROM companies", db_engine)
sectors = pd.read_sql("SELECT company_id, broad_sector FROM sectors", db_engine)

merged = cf_latest.merge(pnl, on=["company_id", "year"], how="left")
merged["cfo_pat_ratio"] = merged["operating_activity"] / merged["net_profit"]

# cashflow_kpis.py's own generate_capital_allocation_output() never actually passes cfo_pat_ratio into classify_capital_allocation() 
# -- so "Shareholder  Returns" (a documented 8th pattern) can never be produced by that function
# as written; it always falls back to "Reinvestor". 
# Computing CFO/PAT here and passing it through, matching the function's own documented intent,
# rather than reproducing that gap. 
# Flagging/documenting gap in cashflow_kpis.py itself.
def classify(row):
    ratio = row["cfo_pat_ratio"] if pd.notna(row["cfo_pat_ratio"]) else None
    return classify_capital_allocation(
        row["operating_activity"], row["investing_activity"], row["financing_activity"],
        cfo_pat_ratio=ratio,
    )
merged["pattern_label"] = merged.apply(classify, axis=1)

merged = merged.merge(companies, on="company_id", how="left").merge(sectors, on="company_id", how="left")

if len(merged) < 92:
    st.caption(f"{len(merged)} of 92 companies have a latest-year cashflow row to classify.")

fig = px.treemap(
    merged, 
    path=["pattern_label", "company_id"], 
    values=[1] * len(merged),
    color="pattern_label",
)
fig.update_layout(height=550, margin=dict(t=20, b=20))

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