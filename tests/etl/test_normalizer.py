"""
Day 2: Unit tests for normalize_year() and normalize_ticker()
Test names match Documentation spec section 27. (Total 39 tests = 25 normalizer_year + 14 normalizer_ticket)
"""


import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src" / "etl"))

from loader import normalize_year, normalize_ticker


# ---------- normalize_year: spec-named tests (Documentation page 40) ----------

def test_year_mar23():
    assert normalize_year("Mar-23") == "2023-03"

def test_year_fy24():
    assert normalize_year("FY24") == "2024-03"

def test_year_dec22():
    assert normalize_year("Dec-22") == "2022-12"

def test_year_garbage():
    assert normalize_year("xyz") == "PARSE_ERROR"


# ---------- normalize_year: additional edge cases (Documentation page 37 table) ----------

def test_year_mar_space_23():
    assert normalize_year("Mar 23") == "2023-03"

def test_year_march_full_name():
    assert normalize_year("March-2023") == "2023-03"

def test_year_plain_int_assumes_march():
    assert normalize_year(2023) == "2023-03"

def test_year_jun23_june_yearend():
    assert normalize_year("Jun-23") == "2023-06"

def test_year_already_normalized_passthrough():
    assert normalize_year("2023-03") == "2023-03"

def test_year_fy_four_digit():
    assert normalize_year("FY2023") == "2023-03"

def test_year_none_is_parse_error():
    assert normalize_year(None) == "PARSE_ERROR"

def test_year_nan_is_parse_error():
    import numpy as np
    assert normalize_year(np.nan) == "PARSE_ERROR"

def test_year_empty_string_is_parse_error():
    assert normalize_year("") == "PARSE_ERROR"

def test_year_out_of_range_low():
    assert normalize_year(1800) == "PARSE_ERROR"

def test_year_out_of_range_high():
    assert normalize_year(2099) == "PARSE_ERROR"

def test_year_boundary_low():
    assert normalize_year(1990) == "1990-03"

def test_year_boundary_high():
    assert normalize_year(2035) == "2035-03"

def test_year_float_input():
    assert normalize_year(2023.0) == "2023-03"

def test_year_whitespace_trimmed():
    assert normalize_year("  Mar-23  ") == "2023-03"

def test_year_sep_month():
    assert normalize_year("Sep-21") == "2021-09"

def test_year_lowercase_month():
    assert normalize_year("mar-23") == "2023-03"

def test_year_negative_is_parse_error():
    assert normalize_year(-2023) == "PARSE_ERROR"

def test_year_random_text_is_parse_error():
    assert normalize_year("N/A") == "PARSE_ERROR"

def test_year_apr_month():
    assert normalize_year("Apr-20") == "2020-04"

def test_year_oct_four_digit_year():
    assert normalize_year("Oct-2022") == "2022-10"


# ---------- normalize_ticker: spec-named tests (Documentation page 40) ----------

def test_ticker_strip():
    assert normalize_ticker(" TCS ") == "TCS"

def test_ticker_lower():
    assert normalize_ticker("tcs") == "TCS"


# ---------- normalize_ticker: additional edge cases (Documentation page 15 note) ----------

def test_ticker_hyphen_preserved():
    assert normalize_ticker("BAJAJ-AUTO") == "BAJAJ-AUTO"

def test_ticker_ampersand_preserved():
    assert normalize_ticker("M&M") == "M&M"

def test_ticker_none():
    assert normalize_ticker(None) is None

def test_ticker_nan():
    import numpy as np
    assert normalize_ticker(np.nan) is None

def test_ticker_empty_string():
    assert normalize_ticker("") is None

def test_ticker_mixed_case():
    assert normalize_ticker("TaTaMoToRs") == "TATAMOTORS"

def test_ticker_already_normalized():
    assert normalize_ticker("TCS") == "TCS"

def test_ticker_lowercase_hyphenated():
    assert normalize_ticker("bajaj-auto") == "BAJAJ-AUTO"

def test_ticker_whitespace_and_case():
    assert normalize_ticker("  hdfcbank  ") == "HDFCBANK"

def test_ticker_numeric_string():
    assert normalize_ticker("500002") == "500002"

def test_ticker_single_char_spacing():
    assert normalize_ticker(" m&m ") == "M&M"

def test_ticker_multiword_company_name():
    assert normalize_ticker("adani green") == "ADANI GREEN"