"""
Sprint 6, Day 41: Data Quality Rule Tests
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src" / "etl"))

import validator  # type: ignore


@pytest.fixture(autouse=True)
def reset_failures():
    """validator.failures is module-level and accumulates -- clear before every test."""
    validator.failures.clear()
    yield
    validator.failures.clear()


def _last_failure():
    assert len(validator.failures) == 1, f"expected exactly 1 failure, got {validator.failures}"
    return validator.failures[0]


def test_dq01_pk_uniqueness_flags_duplicate_id(monkeypatch):
    bad = pd.DataFrame({"id": [1, 1, 2], "company_id": ["A", "B", "C"]})

    def fake_load_table(name):
        if name == "companies":
            return bad
        return pd.DataFrame({"id": [1, 2, 3]})

    monkeypatch.setattr(validator, "load_table", fake_load_table)
    validator.dq01_pk_uniqueness()
    failure = _last_failure()
    assert failure["rule_id"] == "DQ-01"
    assert failure["severity"] == "CRITICAL"


def test_dq02_composite_pk_flags_duplicate_company_year(monkeypatch):
    bad = pd.DataFrame({"company_id": ["TCS", "TCS"], "year": ["2024-03", "2024-03"]})
    monkeypatch.setattr(validator, "load_table", lambda name: bad)
    validator.dq02_composite_pk()
    # Loops over YEAR_TABLES + CALENDAR_YEAR_TABLES (5 tables)
    # -- every one returns the same `bad` frame here, so it fires once per table,
    # not once total (same pattern as dq03/dq16 below).
    assert len(validator.failures) > 0
    assert all(f["rule_id"] == "DQ-02" and f["severity"] == "CRITICAL" for f in validator.failures)


def test_dq03_fk_integrity_flags_orphan_company_id(monkeypatch):
    companies = pd.DataFrame({"id": ["TCS", "INFY"]})
    orphaned = pd.DataFrame({"company_id": ["TCS", "GHOST_TICKER"]})

    def fake_load_table(name):
        return companies if name == "companies" else orphaned

    monkeypatch.setattr(validator, "load_table", fake_load_table)
    validator.dq03_fk_integrity()
    # dq03 loops over every table in ALL_TABLES (minus companies)
    # -- every non-companies table returns the same `orphaned` frame here,
    # so it fires once per table, not once total. Assert on the first, and that every fired failure is correctly attributed.
    assert len(validator.failures) > 0
    assert all(f["rule_id"] == "DQ-03" and f["severity"] == "CRITICAL" for f in validator.failures)


def test_dq04_balance_sheet_balance_flags_mismatch(monkeypatch):
    bad = pd.DataFrame(
        {
            "total_assets": [1000],
            "total_liabilities": [500],
            "equity_capital": [100],
            "reserves": [100],  # 500+100+100=700, way off from 1000
        }
    )
    monkeypatch.setattr(validator, "load_table", lambda name: bad)
    validator.dq04_balance_sheet_balance()
    failure = _last_failure()
    assert failure["rule_id"] == "DQ-04"
    assert failure["severity"] == "WARNING"


def test_dq05_opm_cross_check_flags_large_divergence(monkeypatch):
    ratios = pd.DataFrame(
        {
            "company_id": ["TCS"],
            "year": ["2024-03"],
            "operating_profit_margin_pct": [50.0],
        }
    )
    pnl = pd.DataFrame(
        {
            "company_id": ["TCS"],
            "year": ["2024-03"],
            "operating_profit": [10],
            "sales": [100],  # calc_opm = 10%, diff = 40pp
        }
    )

    def fake_load_table(name):
        return ratios if name == "financial_ratios" else pnl

    monkeypatch.setattr(validator, "load_table", fake_load_table)
    validator.dq05_opm_cross_check()
    failure = _last_failure()
    assert failure["rule_id"] == "DQ-05"
    assert failure["severity"] == "WARNING"


def test_dq06_positive_sales_flags_zero_sales(monkeypatch):
    bad = pd.DataFrame({"sales": [100, 0, -50]})
    monkeypatch.setattr(validator, "load_table", lambda name: bad)
    validator.dq06_positive_sales()
    failure = _last_failure()
    assert failure["rule_id"] == "DQ-06"
    assert failure["severity"] == "WARNING"
    assert "2" in failure["description"]  # both the 0 and the -50 row


def test_dq07_net_cash_consistency_flags_reconciliation_gap(monkeypatch):
    bad = pd.DataFrame(
        {
            "operating_activity": [100],
            "investing_activity": [-20],
            "financing_activity": [-10],
            "net_cash_flow": [999],  # should be 70
        }
    )
    monkeypatch.setattr(validator, "load_table", lambda name: bad)
    validator.dq07_net_cash_consistency()
    failure = _last_failure()
    assert failure["rule_id"] == "DQ-07"
    assert failure["severity"] == "WARNING"


def test_dq08_tax_rate_range_flags_out_of_range(monkeypatch):
    bad = pd.DataFrame({"tax_percentage": [25, -5, 75]})
    monkeypatch.setattr(validator, "load_table", lambda name: bad)
    validator.dq08_tax_rate_range()
    failure = _last_failure()
    assert failure["rule_id"] == "DQ-08"
    assert failure["severity"] == "WARNING"


def test_dq09_dividend_payout_cap_flags_over_100(monkeypatch):
    bad = pd.DataFrame({"dividend_payout_ratio_pct": [50, 150]})
    monkeypatch.setattr(validator, "load_table", lambda name: bad)
    validator.dq09_dividend_payout_cap()
    failure = _last_failure()
    assert failure["rule_id"] == "DQ-09"
    assert failure["severity"] == "WARNING"


def test_dq10_url_format_flags_non_http(monkeypatch):
    bad = pd.DataFrame({"annual_report": ["https://example.com/report.pdf", "not-a-url"]})
    monkeypatch.setattr(validator, "load_table", lambda name: bad)
    validator.dq10_url_format()
    failure = _last_failure()
    assert failure["rule_id"] == "DQ-10"
    assert failure["severity"] == "WARNING"


def test_dq11_eps_sign_check_flags_mismatch(monkeypatch):
    bad = pd.DataFrame(
        {"eps": [5.0, -2.0], "net_profit": [100, 50]}
    )  # 2nd row: eps negative, profit positive
    monkeypatch.setattr(validator, "load_table", lambda name: bad)
    validator.dq11_eps_sign_check()
    failure = _last_failure()
    assert failure["rule_id"] == "DQ-11"
    assert failure["severity"] == "WARNING"


def test_dq12_liabilities_equity_nonneg_flags_negative_total(monkeypatch):
    bad = pd.DataFrame({"equity_capital": [-500], "reserves": [-600], "total_liabilities": [100]})
    monkeypatch.setattr(validator, "load_table", lambda name: bad)
    validator.dq12_liabilities_equity_nonneg()
    failure = _last_failure()
    assert failure["rule_id"] == "DQ-12"
    assert failure["severity"] == "WARNING"


def test_dq13_year_coverage_flags_thin_history(monkeypatch):
    bad = pd.DataFrame(
        {
            "company_id": ["TCS", "TCS", "SHORTCO"],
            "year": ["2022-03", "2023-03", "2024-03"],
        }
    )
    monkeypatch.setattr(validator, "load_table", lambda name: bad)
    validator.dq13_year_coverage()
    failure = _last_failure()
    assert failure["rule_id"] == "DQ-13"
    assert failure["severity"] == "WARNING"


def test_dq14_null_critical_fields_flags_null_company_id(monkeypatch):
    bad = pd.DataFrame({"company_id": ["TCS", None], "year": ["2024-03", "2024-03"]})
    monkeypatch.setattr(validator, "load_table", lambda name: bad)
    validator.dq14_null_critical_fields()
    assert any(f["rule_id"] == "DQ-14" and f["severity"] == "CRITICAL" for f in validator.failures)


def test_dq14_null_critical_fields_flags_parse_error_year(monkeypatch):
    bad = pd.DataFrame({"company_id": ["TCS", "INFY"], "year": ["2024-03", "PARSE_ERROR"]})
    monkeypatch.setattr(validator, "load_table", lambda name: bad)
    validator.dq14_null_critical_fields()
    assert any(f["rule_id"] == "DQ-14" and "year" in f["description"] for f in validator.failures)


def test_dq15_stock_price_positive_flags_non_positive(monkeypatch):
    bad = pd.DataFrame(
        {
            "open_price": [100, -5],
            "high_price": [110, 10],
            "low_price": [95, 5],
            "close_price": [105, 0],
        }
    )
    monkeypatch.setattr(validator, "load_table", lambda name: bad)
    validator.dq15_stock_price_positive()
    assert any(f["rule_id"] == "DQ-15" and f["severity"] == "CRITICAL" for f in validator.failures)


def test_dq16_duplicate_rows_flags_full_duplicates(monkeypatch):
    bad = pd.DataFrame({"a": [1, 1, 2], "b": ["x", "x", "y"]})
    monkeypatch.setattr(validator, "load_table", lambda name: bad)
    validator.dq16_duplicate_rows()
    # Loops over ALL_TABLES, every table returns the same `bad` frame ->
    # fires once per table, all correctly attributed to DQ-16/WARNING.
    assert len(validator.failures) > 0
    assert all(f["rule_id"] == "DQ-16" and f["severity"] == "WARNING" for f in validator.failures)


# ---------- Negative controls: clean data should NOT fire ----------


def test_dq01_clean_data_does_not_fire(monkeypatch):
    clean = pd.DataFrame({"id": [1, 2, 3]})
    monkeypatch.setattr(validator, "load_table", lambda name: clean)
    validator.dq01_pk_uniqueness()
    assert len(validator.failures) == 0


def test_dq06_clean_data_does_not_fire(monkeypatch):
    clean = pd.DataFrame({"sales": [100, 200, 300]})
    monkeypatch.setattr(validator, "load_table", lambda name: clean)
    validator.dq06_positive_sales()
    assert len(validator.failures) == 0
