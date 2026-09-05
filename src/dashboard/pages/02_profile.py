"""Day 22 scaffold -- Company Profile screen. Full charts/badges built Day 23."""
import sys
from pathlib import Path
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils.db import get_companies #type:ignore

st.title("Company Profile")

companies = get_companies()
query = st.text_input("Search company name or ticker")

if query:
    matches = companies[
        companies["company_name"].str.contains(query, case=False, na=False)
        | companies["company_id"].str.contains(query, case=False, na=False)
    ]
    if matches.empty:
        st.warning("Ticker not found - please try another")
    else:
        ticker = st.selectbox("Matches", matches["company_id"] + " - " + matches["company_name"])
        st.caption("Full company card, KPI tiles, and 10-year charts land Day 23.")
else:
    st.caption("Type a company name or ticker to search.")