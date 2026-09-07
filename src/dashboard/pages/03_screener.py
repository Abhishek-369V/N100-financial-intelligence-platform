"""Day 24 — Screener screen: 10 sliders, 6 presets, live table, CSV export."""
import sys
from pathlib import Path
import streamlit as st
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils.db import db_engine

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "screener"))
from engine import load_universe, apply_filter, load_config #type:ignore
from composite_score import compute_composite_score #type:ignore

st.title("Screener")

# Bounds are practical display ranges, 
# not the true data min/max — a few known outliers exist beyond these (e.g. BEL's 4744% ROE, D/E up to 14.9).
# Those companies simply always pass a "min" slider or always fail a "max" slider at the display cap; 
# nothing is excluded from the underlying data.
SLIDERS = [
    ("ROE min (%)",              "roe_min",              0.0, 100.0, 1.0,   0.0),
    ("D/E max",                  "de_max",               0.0, 3.0,   0.1,   3.0),
    ("FCF min (₹ Cr)",           "fcf_min",         -50000.0, 50000.0, 500.0, -50000.0),
    ("Revenue CAGR 5yr min (%)", "revenue_cagr_5yr_min", -10.0, 40.0, 1.0,  -10.0),
    ("PAT CAGR 5yr min (%)",     "pat_cagr_5yr_min",    -30.0, 130.0, 1.0,  -30.0),
    ("OPM min (%)",              "opm_min",               0.0, 100.0, 1.0,   0.0),
    ("P/E max",                  "pe_max",                0.0, 80.0,  1.0,  80.0),
    ("P/B max",                  "pb_max",                0.0, 15.0,  0.5,  15.0),
    ("Dividend Yield min (%)",   "dividend_yield_min",    0.0, 5.0,   0.1,   0.0),
    ("ICR min",                  "icr_min",               0.0, 50.0,  1.0,   0.0),
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
        "Preset also requires Revenue CAGR 3yr > 10% (column doesn't exist yet, "
        "documented Sprint 3 gap) and YoY-declining D/E (needs a 2-year comparison, "
        "not a single-snapshot slider) - neither is applied here, only FCF > 0.",
    ),
}

for _, key, _, _, _, default in SLIDERS:
    if key not in st.session_state:
        st.session_state[key] = default
if "_preset_note" not in st.session_state:
    st.session_state["_preset_note"] = None

st.subheader("Presets")
preset_cols = st.columns(6)
for i, (name, (values, note)) in enumerate(PRESETS.items()):
    if preset_cols[i].button(name, use_container_width=True):
        for k, v in values.items():
            st.session_state[k] = v
        st.session_state["_preset_note"] = f"**{name}**: {note}" if note else None
        st.rerun()

if st.session_state["_preset_note"]:
    st.warning(st.session_state["_preset_note"])

st.divider()

st.sidebar.subheader("Filters")
thresholds = {}
for label, key, lo, hi, step, default in SLIDERS:
    thresholds[key] = st.sidebar.slider(label, lo, hi, key=key, step=step)

config = load_config()
universe = load_universe()

# Same fix as Day 23 Home: load_universe() doesn't merge in companies.roce_percentage or company_name, 
# needed for display + the composite score's ROCE component.
extra = pd.read_sql(
    "SELECT id AS company_id, company_name, roce_percentage FROM companies", db_engine
)
universe = universe.merge(extra, on="company_id", how="left")

filtered = universe.copy()
for label, key, lo, hi, step, default in SLIDERS:
    # A slider left at its "no-op" end (min floor / max ceiling)
    #  shouldn't exclude anyone -- skip applying it entirely.
    is_min_filter = "min" in key
    at_noop = (thresholds[key] == lo) if is_min_filter else (thresholds[key] == hi)
    if at_noop:
        continue
    filtered = apply_filter(filtered, key, thresholds[key], config)

filtered = compute_composite_score(filtered, sector_relative=False)

st.subheader(f"{len(filtered)} companies match your filters")

display_cols = [
    "company_id", "company_name", "broad_sector", "composite_quality_score",
    "return_on_equity_pct", "debt_to_equity", "free_cash_flow_cr",
    "revenue_cagr_5yr", "pat_cagr_5yr", "operating_profit_margin_pct",
    "pe_ratio", "pb_ratio", "dividend_yield_pct", "interest_coverage",
]
display_cols = [c for c in display_cols if c in filtered.columns]
result_table = filtered[display_cols].sort_values("composite_quality_score", ascending=False, na_position="last")

st.dataframe(result_table, hide_index=True, use_container_width=True)

st.download_button(
    "Download CSV",
    data=result_table.to_csv(index=False).encode("utf-8"),
    file_name="screener_results.csv",
    mime="text/csv",
)