"""
tests/etl/test_normalizer.py
Day 2: 35+ unit tests - 20 for normalize_year() and 15 for normalize_ticker()
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src" / "etl"))

from loader import normalize_year, normalize_ticker


# ---------- normalize_year: 20 tests ----------

def test_year_plain_int():
    assert normalize_year(2023) == 2023

def test_year_plain_string():
    assert normalize_year("2023") == 2023

def test_year_float():
    assert normalize_year(2023.0) == 2023

def test_year_fy_two_digit():
    assert normalize_year("FY23") == 2023

def test_year_fy_four_digit():
    assert normalize_year("FY2023") == 2023

def test_year_fy_lowercase():
    assert normalize_year("fy23") == 2023

def test_year_month_year_format():
    assert normalize_year("Mar 2023") == 2023

def test_year_dec_format():
    assert normalize_year("Dec 2012") == 2012

def test_year_none():
    assert normalize_year(None) is None

def test_year_nan():
    import numpy as np
    assert normalize_year(np.nan) is None

def test_year_empty_string():
    assert normalize_year("") is None

def test_year_out_of_range_low():
    assert normalize_year(1800) is None

def test_year_out_of_range_high():
    assert normalize_year(2099) is None

def test_year_with_whitespace():
    assert normalize_year("  2023  ") == 2023

def test_year_fy_with_slash():
    assert normalize_year("FY22/23") is not None  # extracts a valid 4-digit year

def test_year_boundary_low():
    assert normalize_year(1990) == 1990

def test_year_boundary_high():
    assert normalize_year(2035) == 2035

def test_year_garbage_text():
    assert normalize_year("N/A") is None

def test_year_negative():
    assert normalize_year(-2023) is None

def test_year_unexpected_format_returns_none_not_error():
    assert normalize_year("23/03/26") is None


# ---------- normalize_ticker: 15 tests ----------

def test_ticker_plain():
    assert normalize_ticker("ABB") == "ABB"

def test_ticker_lowercase():
    assert normalize_ticker("abb") == "ABB"

def test_ticker_whitespace():
    assert normalize_ticker("  abb  ") == "ABB"

def test_ticker_ns_suffix():
    assert normalize_ticker("ABB.NS") == "ABB"

def test_ticker_bo_suffix():
    assert normalize_ticker("ABB.BO") == "ABB"

def test_ticker_nse_suffix():
    assert normalize_ticker("ABB.NSE") == "ABB"

def test_ticker_bse_suffix():
    assert normalize_ticker("ABB.BSE") == "ABB"

def test_ticker_none():
    assert normalize_ticker(None) is None

def test_ticker_nan():
    import numpy as np
    assert normalize_ticker(np.nan) is None

def test_ticker_empty_string():
    assert normalize_ticker("") is None

def test_ticker_mixed_case():
    assert normalize_ticker("AdAnIeNsOl") == "ADANIENSOL"

def test_ticker_multiword():
    assert normalize_ticker("hdfc bank") == "HDFC BANK"

def test_ticker_lowercase_suffix():
    assert normalize_ticker("abb.ns") == "ABB"

def test_ticker_numeric_ticker():
    assert normalize_ticker("500002") == "500002"

def test_ticker_whitespace_and_suffix():
    assert normalize_ticker("  abb.ns  ") == "ABB"