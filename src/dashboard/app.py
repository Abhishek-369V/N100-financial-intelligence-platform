"""
Day 22(SPRINT4): Streamlit app scaffold — main entry point.
Run with: streamlit run src/dashboard/app.py
    -> Streamlit auto-discovers the 8 screens from the sibling pages/ directory
    -> (src/dashboard/pages/) and builds the sidebar nav from them automatically
    -- no manual nav wiring!..
"""

import streamlit as st

st.set_page_config(
    page_title="Nifty 100 Analytics",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("Nifty 100 Analytics")
st.markdown(
    """
    Welcome to the **N100 Financial Intelligence Platform**.
    """
)

# replace this with once content is build on day 23-25...
st.info(
    "Day 22 scaffold: navigation and the shared cached data loader "
    "(`src/dashboard/utils/db.py`) are wired up. Screen content is built "
    "out Day 23-25 per the sprint schedule."
)