"""Day 22 scaffold -- Peer Comparison screen. Full radar chart/KPI table built Day 24."""
import sys
from pathlib import Path
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils.db import get_peer_group_names #type:ignore

st.title("Peer Comparison")

groups = get_peer_group_names()
if groups:
    st.selectbox("Peer group", groups)
    st.caption("Radar chart (Scatterpolar) and benchmark-highlighted KPI table land Day 24.")
else:
    st.warning("No peer groups found in the database.")