"""Day 22 scaffold -- Annual Reports screen. Full BSE link list built Day 25."""
import sys
from pathlib import Path
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils.db import get_companies #type:ignore

st.title("Annual Reports")

companies = get_companies()
query = st.text_input("Search company name or ticker")
if query:
    matches = companies[companies["company_name"].str.contains(query, case=False, na=False)]
    st.dataframe(matches[["company_id", "company_name"]])
    st.caption("Clickable BSE PDF links with 404 -> red 'Report unavailable' badge land Day 25.")