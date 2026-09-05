"""Day 22 scaffold -- Home screen. Full KPI tiles/donut/table built Day 23."""
import sys
from pathlib import Path
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils.db import get_ratios, get_companies #type:ignore

st.title("Home")

ratios = get_ratios()
companies = get_companies()

if ratios.empty or companies.empty:
    st.warning("No data loaded from nifty100.db yet.")
else:
    st.success(f"Connected to database: {companies['company_id'].nunique()} companies, {ratios['company_id'].nunique()} with ratio data.")
    st.caption("Full KPI tiles, sector donut chart, and top-5 table land Day 23.")