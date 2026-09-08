"""Day 25 — Annual Reports: company search, BSE links, 404 -> red badge."""
import sys
from pathlib import Path
import streamlit as st
import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils.db import get_companies, db_engine

st.set_page_config(layout="wide")

st.title("Annual Reports")

companies = get_companies()
options = (companies["company_id"] + " — " + companies["company_name"]).sort_values().tolist()
picked = st.selectbox("Search company name or ticker", options, index=None, placeholder="Start typing…")

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# What fixed the report unavailable error showing for every company before: 
# BSE's servers were silently rejecting requests that had requests' 
# default Python User-Agent header (a common anti-bot/anti-scraper defense) — so every single link came back looking 
# like a 403/failure, not just TCS/ADANIENSOL, even though the links themselves were fine. 
# 
# Adding a browser-like User-Agent header made BSE treat the request as a normal browser visit, so it stopped blocking it. 
# The 403/405 fallback-to-GET also helps because some servers reject HEAD requests outright but allow GET.

# adding this headers to head and get requests
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"} 

@st.cache_data(ttl=3600)
def check_url_status(url):
    """
    HEAD request with a short timeout; treats any exception (timeout, DNS failure, connection refused) 
    the same as a 404 for display purposes -- the badge just needs to say "can't reach this," not diagnose why.
    Cached 1hr so re-viewing a company doesn't re-hit BSE's servers every rerun.
    """
    try:
        resp = requests.head(url, timeout=5, allow_redirects=True, headers=HEADERS) # added headers
        if resp.status_code in (403, 405): #included 405 
            resp = requests.get(url, timeout=5, stream=True, headers=HEADERS) # added headers
        return resp.status_code
    except requests.RequestException:
        return None

if not picked:
    st.caption("Search a company to see its available annual report years.")
else:
    ticker = picked.split(" — ")[0]
    docs = pd.read_sql(
        'SELECT Year AS year, Annual_Report AS url FROM documents WHERE company_id = :t ORDER BY Year DESC',
        db_engine, params={"t": ticker},
    )

    if docs.empty:
        st.warning("No annual report records found for this company.")
    else:
        st.caption(
            "Link status is checked live against BSE — this can take a few "
            "seconds per report the first time; results are cached for an hour."
        )
        for _, row in docs.iterrows():
            url = row["url"]
            has_link = isinstance(url, str) and url.strip().lower() not in ("", "null", "none")
            col1, col2 = st.columns([1, 4])
            col1.write(f"**{row['year']}**")
            if not has_link:
                col2.error("Report unavailable")
                continue
            status = check_url_status(url)
            if status is not None and status < 400:
                col2.markdown(f"[Open annual report]({url})")
            else:
                col2.error("Report unavailable")
                col2.caption(url)