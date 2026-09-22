"""Screener screen: 10 sliders, presets, live API-backed results and CSV export."""

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils.api_client import APIClientError, get_screener

st.set_page_config(layout="wide")

st.title("Screener")

# Bounds are practical display ranges,
# not the true data min/max — a few known outliers exist beyond these (e.g. BEL's 4744% ROE, D/E up to 14.9).
# Those companies simply always pass a "min" slider or always fail a "max" slider at the display cap;
# nothing is excluded from the underlying data.
SLIDERS = [
    ("ROE min (%)", "roe_min", "min_roe", 0.0, 100.0, 1.0, 0.0),
    ("D/E max", "de_max", "max_de", 0.0, 3.0, 0.1, 3.0),
    ("FCF min (₹ Cr)", "fcf_min", "min_fcf", -50000.0, 50000.0, 500.0, -50000.0),
    ("Revenue CAGR 5yr min (%)", "revenue_cagr_5yr_min", "min_rev_cagr_5yr", -10.0, 40.0, 1.0, -10.0),
    ("PAT CAGR 5yr min (%)", "pat_cagr_5yr_min", "min_pat_cagr_5yr", -30.0, 130.0, 1.0, -30.0),
    ("OPM min (%)", "opm_min", "min_opm", 0.0, 100.0, 1.0, 0.0),
    ("P/E max", "pe_max", "max_pe", 0.0, 80.0, 1.0, 80.0),
    ("P/B max", "pb_max", "max_pb", 0.0, 15.0, 0.5, 15.0),
    ("Dividend Yield min (%)", "dividend_yield_min", "min_dividend_yield", 0.0, 5.0, 0.1, 0.0),
    ("ICR min", "icr_min", "min_icr", 0.0, 50.0, 1.0, 0.0),
]

# Preset -> slider mapping.
# 2 of the 6 presets (Debt-Free Blue Chip, Turnaround Watch) use conditions the 10 sliders can't fully express
# (exact D/E==0 + sales>5000; YoY D/E decline + an unbuilt revenue_cagr_3yr column, per presets.py's own documented gap).
# Each button applies what it can and surfaces what it can't.
PRESETS = {
    "Quality Compounder": (
        {"roe_min": 15.0, "de_max": 1.0, "fcf_min": 1.0, "revenue_cagr_5yr_min": 10.0},
        None,
    ),
    "Value Pick": (
        {"pe_max": 20.0, "pb_max": 3.0, "de_max": 2.0, "dividend_yield_min": 1.0},
        None,
    ),
    "Growth Accelerator": (
        {"pat_cagr_5yr_min": 20.0, "revenue_cagr_5yr_min": 15.0, "de_max": 2.0},
        None,
    ),
    "Dividend Champion": (
        {"dividend_yield_min": 2.0, "fcf_min": 1.0},
        "Preset also requires Dividend Payout < 80% - no payout-ratio slider exists, not applied.",
    ),
    "Debt-Free Blue Chip": (
        {"de_max": 0.0, "roe_min": 12.0},
        "Preset also requires Sales > ₹5,000 Cr - no sales slider exists, not applied.",
    ),
    "Turnaround Watch": (
        {"fcf_min": 1.0},
        "Preset also requires Revenue CAGR 3yr > 10% and YoY-declining D/E; neither condition is represented by the current 10 sliders, so only FCF > 0 is applied.",
    ),
}

for _, key, _, _, _, _, default in SLIDERS:
    if key not in st.session_state:
        st.session_state[key] = default
if "_preset_note" not in st.session_state:
    st.session_state["_preset_note"] = None

st.subheader("Presets")
preset_cols = st.columns(6)
for i, (name, (values, note)) in enumerate(PRESETS.items()):
    if preset_cols[i].button(name, width="stretch"):
        for key, value in values.items():
            st.session_state[key] = value
        st.session_state["_preset_note"] = f"**{name}**: {note}" if note else None
        st.rerun()

if st.session_state["_preset_note"]:
    st.warning(st.session_state["_preset_note"])

st.divider()

with st.sidebar.expander("Screening Filters", expanded=True):
    st.caption("Refine the 92-company universe")
    thresholds = {}
    for label, key, _, lo, hi, step, _ in SLIDERS:
        thresholds[key] = st.slider(label, lo, hi, key=key, step=step)

api_filters = {}
for _, key, api_key, lo, hi, _, _ in SLIDERS:
    is_min_filter = "min" in key
    at_noop = thresholds[key] == (lo if is_min_filter else hi)
    if not at_noop:
        api_filters[api_key] = thresholds[key]

try:
    response = get_screener(**api_filters)
except APIClientError as exc:
    st.error(str(exc))
    st.stop()

result_table = pd.DataFrame(response["companies"])
st.subheader(f"{len(result_table)} companies match your filters")

display_cols = [
    "company_id",
    "company_name",
    "broad_sector",
    "composite_quality_score",
    "return_on_equity_pct",
    "debt_to_equity",
    "free_cash_flow_cr",
    "revenue_cagr_5yr",
    "pat_cagr_5yr",
    "operating_profit_margin_pct",
    "pe_ratio",
    "pb_ratio",
    "dividend_yield_pct",
    "interest_coverage",
]
display_cols = [c for c in display_cols if c in result_table.columns]
result_table = result_table[display_cols]

st.dataframe(result_table, hide_index=True, width="stretch")

st.download_button(
    "Download CSV",
    data=result_table.to_csv(index=False).encode("utf-8"),
    file_name="screener_results.csv",
    mime="text/csv",
)