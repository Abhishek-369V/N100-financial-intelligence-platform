"""
Day 10: CAGR engine — Revenue, PAT (net profit), and EPS growth over 3yr, 5yr, and 10yr windows. 
Handles 6 sign-based edge cases per spec.
"""

import pandas as pd


# ---------- Core CAGR formula with edge-case dispatch ----------

def compute_cagr(start_value, end_value, years):
    """
    CAGR = ((end_value / start_value) ^ (1/years) - 1) * 100

    Returns a tuple: (cagr_value, flag)
    - flag is None when the calculation is valid and cagr_value holds the number.
    - flag holds a string reason when cagr_value is None (calculation invalid/undefined).

    Edge cases, in the order the spec lists them:
    1. Positive start, Positive end  -> compute normally, flag=None
    2. Positive start, Negative end  -> None, flag='DECLINE_TO_LOSS'
    3. Negative start, Positive end  -> None, flag='TURNAROUND'
    4. Negative start, Negative end  -> None, flag='BOTH_NEGATIVE'
    5. Zero start (base)             -> None, flag='ZERO_BASE'
    6. Fewer than `years` of data available -> handled by caller (compute_cagr_for_window),
       since this function only ever sees two already-selected values, not a full series.
    """
    if start_value is None or end_value is None:
        return None, "INSUFFICIENT"

    if start_value == 0:
        return None, "ZERO_BASE"

    if start_value > 0 and end_value < 0:
        return None, "DECLINE_TO_LOSS"

    if start_value < 0 and end_value > 0:
        return None, "TURNAROUND"

    if start_value < 0 and end_value < 0:
        return None, "BOTH_NEGATIVE"

    # Both positive -> normal computation
    cagr_value = ((end_value / start_value) ** (1 / years) - 1) * 100
    return round(cagr_value, 2), None


def compute_all_cagr_windows(df, company_id, metric_col):
    """
    Computes CAGR for a single metric across all 3 required windows: 3yr, 5yr, 10yr.
    Returns a dict with value+flag for each window — this is what actually
    gets called for Revenue, PAT, and EPS (3 metrics * 3 windows = 9 total
    CAGR values per company, matching the spec's '3 metrics * 3 windows').
    """
    results = {}
    for window in [3, 5, 10]:
        value, flag = compute_cagr_for_window(df, company_id, metric_col, "year", window)
        results[f"{metric_col}_cagr_{window}yr"] = value
        results[f"{metric_col}_cagr_{window}yr_flag"] = flag
    return results


def compute_cagr_for_window(df, company_id, metric_col, year_col, window_years):
    """
    Selects the start and end values for a company from a DataFrame of
    yearly financials, then delegates to compute_cagr().

    df: must contain columns [company_id_col, year_col, metric_col], one row
        per company-year, sorted or sortable by year.
    window_years: 3, 5, or 10 — how many years back to measure from the latest year.

    Handles edge case 6 (insufficient data) BEFORE calling compute_cagr —
    if the company doesn't have at least `window_years + 1` distinct years
    of data ending at its latest year, we can't measure a clean window at all.
    """
    company_data = df[df["company_id"] == company_id].copy()
    company_data = company_data.sort_values(year_col)

    if len(company_data) < window_years + 1:
        return None, "INSUFFICIENT"

    end_row = company_data.iloc[-1]
    start_row_index = -1 - window_years

    # Guard against index out of range (belt-and-suspenders on top of the length check above)
    if abs(start_row_index) > len(company_data):
        return None, "INSUFFICIENT"

    start_row = company_data.iloc[start_row_index]

    start_value = start_row[metric_col]
    end_value = end_row[metric_col]

    if pd.isna(start_value) or pd.isna(end_value):
        return None, "INSUFFICIENT"

    return compute_cagr(start_value, end_value, window_years)


# ---------- Metric-specific wrappers (Revenue, PAT, EPS * 3/5/10yr) ----------

def revenue_cagr(df, company_id, window_years):
    """Revenue (sales) CAGR for a given window. df must have a 'sales' column."""
    return compute_cagr_for_window(df, company_id, metric_col="sales", year_col="year", window_years=window_years)


def pat_cagr(df, company_id, window_years):
    """PAT (net profit) CAGR for a given window. df must have a 'net_profit' column."""
    return compute_cagr_for_window(df, company_id, metric_col="net_profit", year_col="year", window_years=window_years)


def eps_cagr(df, company_id, window_years):
    """EPS CAGR for a given window. df must have an 'eps' column."""
    return compute_cagr_for_window(df, company_id, metric_col="eps", year_col="year", window_years=window_years)