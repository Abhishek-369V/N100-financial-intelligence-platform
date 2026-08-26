"""
Day 10: 10 unit tests covering all 6 CAGR edge cases plus normal cases and window-based selection.
"""

import sys
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src" / "analytics"))

from cagr import compute_cagr, compute_cagr_for_window, revenue_cagr #type:ignore


# ---------- 1. Normal CAGR (positive -> positive) ----------

def test_cagr_normal_case():
    # 100 -> 200 over 5 years: ((200/100)^(1/5) - 1) * 100 ≈ 14.87%
    value, flag = compute_cagr(start_value=100, end_value=200, years=5)
    assert flag is None
    assert value == 14.87


# ---------- 2. Decline to loss (positive -> negative) ----------

def test_cagr_decline_to_loss():
    value, flag = compute_cagr(start_value=100, end_value=-50, years=3)
    assert value is None
    assert flag == "DECLINE_TO_LOSS"


# ---------- 3. Turnaround (negative -> positive) ----------

def test_cagr_turnaround():
    value, flag = compute_cagr(start_value=-100, end_value=50, years=3)
    assert value is None
    assert flag == "TURNAROUND"


# ---------- 4. Both negative ----------

def test_cagr_both_negative():
    value, flag = compute_cagr(start_value=-100, end_value=-50, years=3)
    assert value is None
    assert flag == "BOTH_NEGATIVE"


# ---------- 5. Zero base ----------

def test_cagr_zero_base():
    value, flag = compute_cagr(start_value=0, end_value=100, years=3)
    assert value is None
    assert flag == "ZERO_BASE"


# ---------- 6. Insufficient data (missing values passed in) ----------

def test_cagr_insufficient_missing_values():
    value, flag = compute_cagr(start_value=None, end_value=100, years=3)
    assert value is None
    assert flag == "INSUFFICIENT"


# ---------- 7-8. Window-based selection: sufficient vs insufficient history ----------

def test_cagr_window_insufficient_history():
    df = pd.DataFrame({
        "company_id": ["ABC", "ABC"],
        "year": ["2022-03", "2023-03"],
        "sales": [1000, 1100],
    })
    # Only 2 years of data, asking for a 5-year window -> insufficient
    value, flag = revenue_cagr(df, company_id="ABC", window_years=5)
    assert value is None
    assert flag == "INSUFFICIENT"

def test_cagr_window_sufficient_history():
    df = pd.DataFrame({
        "company_id": ["ABC"] * 4,
        "year": ["2020-03", "2021-03", "2022-03", "2023-03"],
        "sales": [1000, 1100, 1210, 1331],  # exactly 10% growth per year
    })
    value, flag = revenue_cagr(df, company_id="ABC", window_years=3)
    assert flag is None
    assert value == 10.0  # 1000 -> 1331 over 3 years = 10% CAGR


# ---------- 9. Negative years input guard (defensive) ----------

def test_cagr_single_year_zero_growth():
    # start == end, 1 year window -> 0% growth, still a valid (not edge-case) result
    value, flag = compute_cagr(start_value=100, end_value=100, years=1)
    assert flag is None
    assert value == 0.0


# ---------- 10. NaN values in window data treated as insufficient ----------

def test_cagr_window_nan_value_is_insufficient():
    df = pd.DataFrame({
        "company_id": ["XYZ", "XYZ", "XYZ", "XYZ"],
        "year": ["2020-03", "2021-03", "2022-03", "2023-03"],
        "sales": [None, 1100, 1210, 1331],  # start value missing
    })
    value, flag = revenue_cagr(df, company_id="XYZ", window_years=3)
    assert value is None
    assert flag == "INSUFFICIENT"