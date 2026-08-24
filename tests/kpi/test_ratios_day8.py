"""
tests/kpi/test_ratios_day8.py
Day 8: 8 unit tests for profitability ratios.
Spec requires coverage of: normal case, zero denominator (None), negative equity (None), OPM cross-check mismatch.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src" / "analytics"))

from ratios import (
    net_profit_margin, operating_profit_margin,
    return_on_equity, return_on_capital_employed, return_on_assets
)


# ---------- Normal cases (2 tests) ----------

def test_npm_normal_case():
    assert net_profit_margin(net_profit=100, sales=1000) == 10.0

def test_roe_normal_case():
    assert return_on_equity(net_profit=150, equity_capital=200, reserves=800) == 15.0


# ---------- Zero denominator -> None (2 tests) ----------

def test_npm_zero_sales_returns_none():
    assert net_profit_margin(net_profit=100, sales=0) is None

def test_roa_zero_assets_returns_none():
    assert return_on_assets(net_profit=100, total_assets=0) is None


# ---------- Negative equity -> None (2 tests) ----------

def test_roe_negative_equity_returns_none():
    # equity_capital + reserves = 100 + (-500) = -400 (negative net worth)
    assert return_on_equity(net_profit=50, equity_capital=100, reserves=-500) is None

def test_roce_negative_capital_employed_returns_none():
    assert return_on_capital_employed(ebit=100, equity_capital=50, reserves=-300, borrowings=20) is None


# ---------- OPM cross-check mismatch (2 tests) ----------

def test_opm_cross_check_matches_no_flag():
    # calculated = 200/1000*100 = 20.0, reported = 20.5 -> diff 0.5, within 1pp tolerance
    value, mismatch = operating_profit_margin(operating_profit=200, sales=1000, reported_opm=20.5)
    assert value == 20.0
    assert mismatch is False

def test_opm_cross_check_mismatch_flagged():
    # calculated = 200/1000*100 = 20.0, reported = 25.0 -> diff 5.0, exceeds 1pp tolerance
    value, mismatch = operating_profit_margin(operating_profit=200, sales=1000, reported_opm=25.0)
    assert value == 20.0
    assert mismatch is True 