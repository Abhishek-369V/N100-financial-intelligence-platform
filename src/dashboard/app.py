""" 
Day 22(SPRINT4): Streamlit app scaffold: main entry point. 

Run with: streamlit run src/dashboard/app.py 
        -> Streamlit auto-discovers the 8 screens from the sibling pages/ directory 
        -> (src/dashboard/pages/) and builds the sidebar nav from them automatically 
        -- no manual nav wiring!.. 

MODIFY APP.py - BY REPLACING PLACEHOLDER AND CHANGE IN STYLING.. 
    NOW: The entrypoint owns the shared application configuration and navigation. 
        Individual screens remain in `src/dashboard/pages/ so their existing 
        analytics/UI logic can stay isolated from the app shell.
"""

from pathlib import Path

import streamlit as st

from utils.api_client import APIClientError, health

BASE_DIR = Path(__file__).resolve().parent

st.set_page_config(
    page_title="Nifty 100 Financial Intelligence",
    page_icon="./assets/graph.png",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Shared visual polish for the application shell. The analytical pages keep
# their own content/UI logic; these rules only make Streamlit's native shell
# and status messages fit the Deep Navy + Teal theme.

# Custom CSS targeting the Bloomberg Deep Slate layout rules
st.markdown(
    """
    <style>
        /* 1. Teal coloring to Sidebar */
        [data-testid="stSidebarNav"] span[data-testid="stIconMaterial"], 
        header [data-testid="stIconMaterial"] {
            color: #00D2C4 !important;
        }
        
        /* 2. Softened sidebar dividing boundary line */
        [data-testid="stSidebar"] {
            border-right: 1px solid rgba(128, 128, 128, 0.18);
        }

        /* Keep sidebar content in its own scrollable layer. This prevents
           contextual controls from visually slipping under the branding
           block when the sidebar is tall (navigation + filters). 
        */
        [data-testid="stSidebarContent"] {
            overflow-y: auto !important;
            overscroll-behavior: contain;
        }
        
        /* 3. Native Streamlit status messages: quieter, compact, theme-aligned.   
           Semantic icon colors are retained so warning/info/error/success are
           still immediately distinguishable without the bright default cards.
        */
        [data-testid="stAlert"] {
            background: rgba(13, 27, 42, 0.72) !important;
            border: 1px solid rgba(148, 163, 184, 0.18) !important;
            border-left: 3px solid rgba(0, 210, 196, 0.72) !important;
            border-radius: 8px !important;
            box-shadow: none !important;
            padding: 0.55rem 0.8rem !important;
            margin: 0.5rem 0 0.75rem 0 !important;
        }

        [data-testid="stAlert"] p {
            color: #CBD5E1 !important;
            font-size: 0.88rem !important;
        }

        [data-testid="stAlert"] [data-testid="stMarkdownContainer"] {
            color: #CBD5E1 !important;
        }

        /* Keep the message icon visually aligned with the text. */
        [data-testid="stAlert"] svg {
            margin-top: 0.05rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# Streamlit's st.navigation/st.Page API gives us explicit control over labels,
# icons, URL paths, and section grouping while preserving the existing page files.
HOME = st.Page(
    str(BASE_DIR / "pages" / "01_home.py"),
    title="Home",
    icon=":material/home:",
    url_path="home",
    default=True,
)
PROFILE = st.Page(
    str(BASE_DIR / "pages" / "02_profile.py"),
    title="Company Profile",
    icon=":material/business:",
    url_path="profile",
)
SCREENER = st.Page(
    str(BASE_DIR / "pages" / "03_screener.py"),
    title="Screener",
    icon=":material/filter_alt:",
    url_path="screener",
)
PEERS = st.Page(
    str(BASE_DIR / "pages" / "04_peers.py"),
    title="Peer Comparison",
    icon=":material/groups:",
    url_path="peers",
)
TRENDS = st.Page(
    str(BASE_DIR / "pages" / "05_trends.py"),
    title="Trend Analysis",
    icon=":material/trending_up:",
    url_path="trends",
)
SECTORS = st.Page(
    str(BASE_DIR / "pages" / "06_sectors.py"),
    title="Sector Analysis",
    icon=":material/donut_large:",
    url_path="sectors",
)
CAPITAL = st.Page(
    str(BASE_DIR / "pages" / "07_capital.py"),
    title="Capital Allocation",
    icon=":material/account_balance:",
    url_path="capital-allocation",
)
REPORTS = st.Page(
    str(BASE_DIR / "pages" / "08_reports.py"),
    title="Annual Reports",
    icon=":material/description:",
    url_path="reports",
)

pg = st.navigation(
    {
        "Overview": [HOME, PROFILE],
        "Analysis": [SCREENER, PEERS, TRENDS, SECTORS, CAPITAL],
        "Reports": [REPORTS],
    },
    position="sidebar",
    expanded=True,
)

# A small shell-level indicator makes the full-stack connection visible while
# keeping page content focused on analysis. 
# The status also reflects the hosted backend cold-start window handled by the API client.
backend_status = st.sidebar.empty()


def _show_backend_attempt(attempt: int, total_attempts: int) -> None:
    """Update the sidebar while the shell is establishing the API connection."""
    if attempt == 1:
        backend_status.caption("Backend · connecting...")
    else:
        backend_status.caption("Backend · waking up...")


try:
    backend_health = health(on_attempt=_show_backend_attempt)
    backend_status.caption("Backend · connected")
except APIClientError as exc:
    backend_status.caption("Backend · unavailable")

    # Keep the final message compact and neutral. The API client provides a
    # short local-development instruction or a concise deployed recovery note.
    st.sidebar.info(str(exc))

pg.run()