"""
Sprint 6, Day 41: Unit tests for the loader's row counts and column names.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src" / "etl"))

from loader import load_core_file, load_supporting_file, CORE_FILES, SUPPORTING_FILES


# ---------- Core files (banner row at 0, real header at row 1) ----------

def test_companies_row_count():
    df = load_core_file(CORE_FILES["companies"])
    assert len(df) == 92


def test_companies_columns():
    df = load_core_file(CORE_FILES["companies"])
    assert {"id", "company_name", "roce_percentage", "roe_percentage"}.issubset(df.columns)


def test_profitandloss_row_count():
    df = load_core_file(CORE_FILES["profitandloss"])
    assert len(df) == 1276


def test_profitandloss_columns():
    df = load_core_file(CORE_FILES["profitandloss"])
    assert {"company_id", "year", "sales", "net_profit", "eps"}.issubset(df.columns)


def test_balancesheet_row_count():
    df = load_core_file(CORE_FILES["balancesheet"])
    assert len(df) == 1312


def test_balancesheet_columns():
    df = load_core_file(CORE_FILES["balancesheet"])
    assert {"company_id", "year", "equity_capital", "borrowings", "total_assets"}.issubset(df.columns)


def test_cashflow_row_count():
    df = load_core_file(CORE_FILES["cashflow"])
    assert len(df) == 1187


def test_cashflow_columns():
    df = load_core_file(CORE_FILES["cashflow"])
    assert {"company_id", "year", "operating_activity", "investing_activity", "financing_activity"}.issubset(df.columns)


def test_documents_row_count():
    df = load_core_file(CORE_FILES["documents"])
    assert len(df) == 1585


def test_analysis_row_count():
    # GAP: only 20 rows / 5 companies of 92 have any analysis data at all --
    # confirmed a genuine source-data coverage gap in Sprint 5 Day 29, not a loader bug. 
    # Asserting the real count so a future data refresh that silently drops rows gets caught, not asserting an aspirational 92.
    df = load_core_file(CORE_FILES["analysis"])
    assert len(df) == 20


def test_prosandcons_row_count():
    # GAP: same as analysis.xlsx -- only 16 of 92 companies have raw
    # pros/cons data (Sprint 5 Day 30 doesn't use this file at all, it generates pros/cons independently from financial_ratios instead).
    df = load_core_file(CORE_FILES["prosandcons"])
    assert len(df) == 16


# ---------- Supporting files (header at row 0, no banner) ----------

def test_sectors_row_count_and_columns():
    df = load_supporting_file(SUPPORTING_FILES["sectors"])
    assert len(df) == 92
    assert {"company_id", "broad_sector", "sub_sector", "market_cap_category"}.issubset(df.columns)


def test_stock_prices_row_count():
    df = load_supporting_file(SUPPORTING_FILES["stock_prices"])
    assert len(df) == 5520


def test_market_cap_row_count_and_columns():
    df = load_supporting_file(SUPPORTING_FILES["market_cap"])
    assert len(df) == 552
    assert {"company_id", "year", "pe_ratio", "dividend_yield_pct"}.issubset(df.columns)


def test_financial_ratios_row_count():
    df = load_supporting_file(SUPPORTING_FILES["financial_ratios"])
    assert len(df) == 1184


def test_financial_ratios_columns():
    # NOTE: revenue_cagr_5yr, pat_cagr_5yr, eps_cagr_5yr are NOT in the raw
    # file -- confirmed by running this test against the actual file (it originally asserted them and failed). 
    # Those are computed later by src/analytics/populate_ratios.py and only exist in the DB table, not
    # the raw source. Asserting only what's genuinely present at load time.
    df = load_supporting_file(SUPPORTING_FILES["financial_ratios"])
    assert {"return_on_equity_pct", "debt_to_equity", "operating_profit_margin_pct"}.issubset(df.columns)


def test_peer_groups_row_count_and_columns():
    df = load_supporting_file(SUPPORTING_FILES["peer_groups"])
    assert len(df) == 56
    assert {"peer_group_name", "company_id", "is_benchmark"}.issubset(df.columns)


# ---------- Cross-file sanity ----------

def test_all_core_and_supporting_files_load_without_error():
    """Every registered file actually loads -- catches a renamed/missing
    file immediately rather than failing deep inside a later pipeline step."""
    for filename in CORE_FILES.values():
        df = load_core_file(filename)
        assert len(df) > 0
    for filename in SUPPORTING_FILES.values():
        df = load_supporting_file(filename)
        assert len(df) > 0


def test_twelve_files_registered():
    assert len(CORE_FILES) == 7
    assert len(SUPPORTING_FILES) == 5
    assert len(CORE_FILES) + len(SUPPORTING_FILES) == 12