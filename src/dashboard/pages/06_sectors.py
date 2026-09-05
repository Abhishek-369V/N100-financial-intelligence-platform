"""Day 22 scaffold -- Sector Analysis screen. Full bubble chart built Day 25."""
import sys
from pathlib import Path
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils.db import get_sectors #type:ignore

st.title("Sector Analysis")

sectors = get_sectors()
if not sectors.empty:
    st.selectbox("Sector", sorted(sectors["broad_sector"].dropna().unique()))
    st.caption("Revenue/ROE/Market-Cap bubble chart and sector median bar chart land Day 25.")
else:
    st.warning("No sector data found.")