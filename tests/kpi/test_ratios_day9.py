"""
tests/kpi/test_ratios_day9.py
Day 9: 13 unit tests covering all 7 leverage & efficiency functions. ---> 13 because, covering all 7 functions properly 
       (including both branches of the flag/label functions) genuinely needs more than 8 to be meaningful 
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src" / "analytics"))

from ratios import ( #type: ignore
    debt_to_equity, high_leverage_flag, interest_coverage_ratio,
    icr_label, icr_warning_flag, net_debt, asset_turnover
)


# 1. D/E debt-free returns 0
def test_de_debt_free_returns_zero():
    assert debt_to_equity(borrowings=0, equity_capital=100, reserves=400) == 0.0

# 2. D/E normal case
def test_de_normal_case():
    assert debt_to_equity(borrowings=250, equity_capital=100, reserves=150) == 1.0

# 3. ICR interest=0 returns None
def test_icr_zero_interest_returns_none():
    assert interest_coverage_ratio(operating_profit=200, other_income=10, interest=0) is None

# 4. ICR normal case
def test_icr_normal_case():
    assert interest_coverage_ratio(operating_profit=200, other_income=10, interest=50) == 4.2

# 5. ICR label = Debt Free
def test_icr_label_debt_free_when_none():
    assert icr_label(icr_value=None) == "Debt Free"

# 6. High D/E flag — triggered for non-Financials, suppressed for Financials
def test_high_leverage_flag_triggered_non_financial():
    assert high_leverage_flag(debt_to_equity_value=6.0, broad_sector="Industrials") is True

def test_high_leverage_flag_suppressed_for_financials():
    assert high_leverage_flag(debt_to_equity_value=8.0, broad_sector="Financials") is False

# 7. ICR warning flag — below 1.5 threshold
def test_icr_warning_flag_triggered_below_threshold():
    assert icr_warning_flag(icr_value=1.2) is True

def test_icr_warning_flag_not_triggered_above_threshold():
    assert icr_warning_flag(icr_value=3.0) is False

# 8. Net Debt — can be negative (net cash position)
def test_net_debt_positive_when_debt_exceeds_investments():
    assert net_debt(borrowings=500, investments=200) == 300

def test_net_debt_negative_when_investments_exceed_debt():
    assert net_debt(borrowings=100, investments=400) == -300

# 9. Asset Turnover — normal + zero-assets guard
def test_asset_turnover_normal_case():
    assert asset_turnover(sales=1500, total_assets=1000) == 1.5

def test_asset_turnover_zero_assets_returns_none():
    assert asset_turnover(sales=1000, total_assets=0) is None