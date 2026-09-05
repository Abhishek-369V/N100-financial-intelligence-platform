"""
Day 22 (SPRINT4): Shared data-loader module for the Streamlit dashboard.
                -> Every query function is cached with @st.cache_data(ttl=600) per spec.

NOTE: (flagging, not silently working around): 
-> get_valuation() reads output/valuation_summary.xlsx, which doesn't exist yet -- it's a Day 26 deliverable. 
-> Until then this returns an empty DataFrame with the expected columns rather than raising, 
   so Days 22-25 screens that don't touch valuation aren't blocked. 
-> Any screen that calls get_valuation() before Day 26 will just render "no data" -- not crash.
"""

import pandas as pd
import streamlit as st
from pathlib import Path
from sqlalchemy import create_engine

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
DB_PATH = BASE_DIR / "db" / "nifty100.db"
VALUATION_PATH = BASE_DIR / "output" / "valuation_summary.xlsx"

db_engine = create_engine(f"sqlite:///{DB_PATH}")


@st.cache_data(ttl=600)
def get_companies():
    """All 92 companies with sector info joined in (used for search/dropdowns)."""
    df = pd.read_sql(
        "SELECT id AS company_id, company_name, about_company, website, roce_percentage, roe_percentage FROM companies",
        db_engine,
    )
    sectors = pd.read_sql("SELECT company_id, broad_sector, sub_sector FROM sectors", db_engine)
    return df.merge(sectors, on="company_id", how="left")


@st.cache_data(ttl=600)
def get_ratios(ticker=None, year=None):
    """
    financial_ratios rows. ticker filters to one company; 
    year filters to one fiscal year (both optional -- omitting both returns the full table,
    which callers use for universe-wide aggregates like the Home screen KPIs).
    """
    query = "SELECT * FROM financial_ratios WHERE 1=1"
    params = {}
    if ticker is not None:
        query += " AND company_id = :ticker"
        params["ticker"] = ticker
    if year is not None:
        query += " AND year = :year"
        params["year"] = year
    return pd.read_sql(query, db_engine, params=params)


@st.cache_data(ttl=600)
def get_pl(ticker):
    """profitandloss history for one company, sorted by year."""
    return pd.read_sql(
        "SELECT * FROM profitandloss WHERE company_id = :ticker ORDER BY year",
        db_engine, params={"ticker": ticker},
    )


@st.cache_data(ttl=600)
def get_bs(ticker):
    """balancesheet history for one company, sorted by year."""
    return pd.read_sql(
        "SELECT * FROM balancesheet WHERE company_id = :ticker ORDER BY year",
        db_engine, params={"ticker": ticker},
    )


@st.cache_data(ttl=600)
def get_cf(ticker):
    """cashflow history for one company, sorted by year."""
    return pd.read_sql(
        "SELECT * FROM cashflow WHERE company_id = :ticker ORDER BY year",
        db_engine, params={"ticker": ticker},
    )


@st.cache_data(ttl=600)
def get_sectors():
    """Full sectors table (broad_sector, sub_sector, weight, market cap category)."""
    return pd.read_sql("SELECT * FROM sectors", db_engine)


@st.cache_data(ttl=600)
def get_peers(group_name):
    """
    Peer group membership + benchmark flag for one named group, joined
    with the latest-year financial_ratios row per member (same
    latest-year-snapshot pattern as engine.py / peer.py from Sprint 3).
    """
    members = pd.read_sql(
        "SELECT company_id, is_benchmark FROM peer_groups WHERE peer_group_name = :g",
        db_engine, params={"g": group_name},
    )
    if members.empty:
        return members

    ratios = pd.read_sql("SELECT * FROM financial_ratios", db_engine)
    ratios_latest = ratios.sort_values("year").groupby("company_id").last().reset_index()

    companies = pd.read_sql("SELECT id AS company_id, company_name FROM companies", db_engine)

    out = members.merge(ratios_latest, on="company_id", how="left")
    out = out.merge(companies, on="company_id", how="left")
    return out


@st.cache_data(ttl=600)
def get_valuation(ticker=None):
    """
    Reads output/valuation_summary.xlsx (Day 26 deliverable). Returns an
    empty frame with the spec'd columns if the file doesn't exist yet,
    rather than raising -- see module docstring.
    """
    expected_cols = [
        "company_id", "company_name", "sector", "pe_ratio", "pb_ratio",
        "ev_ebitda", "fcf_yield_pct", "pe_5yr_median", "pe_vs_sector_median_pct", "flag",
    ]
    if not VALUATION_PATH.exists():
        return pd.DataFrame(columns=expected_cols)

    df = pd.read_excel(VALUATION_PATH)
    if ticker is not None and "company_id" in df.columns:
        df = df[df["company_id"] == ticker]
    return df


@st.cache_data(ttl=600)
def get_peer_group_names():
    """Convenience helper: the 11 distinct peer group names, for the Peers screen dropdown."""
    df = pd.read_sql("SELECT DISTINCT peer_group_name FROM peer_groups ORDER BY peer_group_name", db_engine)
    return df["peer_group_name"].tolist()