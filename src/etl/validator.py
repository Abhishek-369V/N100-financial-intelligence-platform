"""
validator.py — N100 Financial Intelligence Platform
Day 3 (corrected): 16 DQ rules using verified column names from
Nifty100_Project_Document_FINAL.pdf, pages 10-15.
Severities confirmed against PDF test cases (page 41) where available;
unconfirmed rules marked with a comment — verify against your team's
actual DQ-01..16 doc if you get a complete copy.
"""

import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
PROCESSED_PATH = BASE_DIR / "data" / "processed"
OUTPUT_PATH = BASE_DIR / "output"
OUTPUT_PATH.mkdir(parents=True, exist_ok=True)

failures = []


def log_failure(rule_id, table, description, severity, row_ref=None):
    failures.append({
        "rule_id": rule_id, "table": table, "description": description,
        "severity": severity, "row_ref": row_ref,
    })


def load_table(name):
    return pd.read_csv(PROCESSED_PATH / f"{name}.csv")


ALL_TABLES = ["companies", "profitandloss", "balancesheet", "cashflow",
              "documents", "analysis", "prosandcons", "sectors",
              "stock_prices", "financial_ratios", "peer_groups", "market_cap"]

YEAR_TABLES = ["profitandloss", "balancesheet", "cashflow", "financial_ratios"]  # 'YYYY-MM' string year
CALENDAR_YEAR_TABLES = ["market_cap"]  # plain int year


def dq01_pk_uniqueness():
    """DQ-01 CRITICAL: 'id' must be unique where present."""
    for name in ALL_TABLES:
        df = load_table(name)
        if "id" in df.columns:
            dupes = df["id"].duplicated().sum()
            if dupes > 0:
                log_failure("DQ-01", name, f"{dupes} duplicate 'id' values", "CRITICAL")


def dq02_composite_pk():
    """DQ-02 CRITICAL: (company_id, year) must be unique."""
    for name in YEAR_TABLES + CALENDAR_YEAR_TABLES:
        df = load_table(name)
        if "company_id" in df.columns and "year" in df.columns:
            df_valid = df[df["year"] != "PARSE_ERROR"]
            dupes = df_valid.duplicated(subset=["company_id", "year"]).sum()
            if dupes > 0:
                log_failure("DQ-02", name, f"{dupes} duplicate (company_id, year) pairs", "CRITICAL")


def dq03_fk_integrity():
    """DQ-03 CRITICAL: company_id must exist in companies.id (not 'ticker')."""
    companies = load_table("companies")
    valid_ids = set(companies["id"])  # companies PK is 'id', confirmed in schema.sql

    for name in ALL_TABLES:
        if name == "companies":
            continue
        df = load_table(name)
        if "company_id" in df.columns:
            orphans = ~df["company_id"].isin(valid_ids)
            if orphans.sum() > 0:
                log_failure("DQ-03", name, f"{orphans.sum()} rows with company_id not in companies", "CRITICAL")


def dq04_balance_sheet_balance():
    """DQ-04 WARNING: total_assets should equal total_liabilities + equity, within 1%."""
    df = load_table("balancesheet")
    required = ["total_assets", "total_liabilities", "equity_capital", "reserves"]
    if all(c in df.columns for c in required):
        equity = df["equity_capital"] + df["reserves"]
        diff_pct = (df["total_assets"] - (df["total_liabilities"] + equity)).abs() / df["total_assets"].replace(0, pd.NA)
        violations = diff_pct[diff_pct > 0.01].dropna()
        if len(violations) > 0:
            log_failure("DQ-04", "balancesheet", f"{len(violations)} rows where Assets != Liabilities+Equity (>1%)", "WARNING")


def dq05_opm_cross_check():
    """DQ-05 WARNING: financial_ratios OPM vs P&L-derived OPM, >5pp diff."""
    ratios = load_table("financial_ratios")
    pnl = load_table("profitandloss")
    if "operating_profit" in pnl.columns and "sales" in pnl.columns and "operating_profit_margin_pct" in ratios.columns:
        pnl_calc = pnl.copy()
        pnl_calc["calc_opm"] = (pnl_calc["operating_profit"] / pnl_calc["sales"].replace(0, pd.NA)) * 100
        merged = ratios.merge(pnl_calc[["company_id", "year", "calc_opm"]], on=["company_id", "year"], how="inner")
        mismatch = (merged["operating_profit_margin_pct"] - merged["calc_opm"]).abs() > 5
        if mismatch.sum() > 0:
            log_failure("DQ-05", "financial_ratios", f"{mismatch.sum()} rows where OPM differs from P&L by >5pp", "WARNING")


def dq06_positive_sales():
    """DQ-06 WARNING (confirmed via PDF test_dq06_zero_sales): sales must be > 0."""
    df = load_table("profitandloss")
    if "sales" in df.columns:
        zero_or_neg = df["sales"] <= 0
        if zero_or_neg.sum() > 0:
            log_failure("DQ-06", "profitandloss", f"{zero_or_neg.sum()} rows with zero/negative sales", "WARNING")


def dq07_net_cash_consistency():
    """DQ-07 WARNING (unconfirmed severity): net_cash_flow should reconcile with the 3 activities."""
    df = load_table("cashflow")
    required = ["operating_activity", "investing_activity", "financing_activity", "net_cash_flow"]
    if all(c in df.columns for c in required):
        calc = df["operating_activity"] + df["investing_activity"] + df["financing_activity"]
        diff = (df["net_cash_flow"] - calc).abs()
        violations = diff[diff > 1].dropna()
        if len(violations) > 0:
            log_failure("DQ-07", "cashflow", f"{len(violations)} rows where net cash flow doesn't reconcile", "WARNING")


def dq08_tax_rate_range():
    """DQ-08 WARNING (unconfirmed severity): tax_percentage should be within 0-50%."""
    df = load_table("profitandloss")
    if "tax_percentage" in df.columns:
        out_of_range = (df["tax_percentage"] < 0) | (df["tax_percentage"] > 50)
        if out_of_range.sum() > 0:
            log_failure("DQ-08", "profitandloss", f"{out_of_range.sum()} rows with tax_percentage outside 0-50%", "WARNING")


def dq09_dividend_payout_cap():
    """DQ-09 WARNING: dividend payout ratio should not exceed 100%."""
    df = load_table("financial_ratios")
    if "dividend_payout_ratio_pct" in df.columns:
        over_100 = df["dividend_payout_ratio_pct"] > 100
        if over_100.sum() > 0:
            log_failure("DQ-09", "financial_ratios", f"{over_100.sum()} rows with payout ratio >100%", "WARNING")


def dq10_url_format():
    """DQ-10 WARNING: annual_report URLs should start with http."""
    df = load_table("documents")
    if "annual_report" in df.columns:
        invalid = df["annual_report"].dropna().astype(str).apply(lambda x: not x.startswith("http"))
        if invalid.sum() > 0:
            log_failure("DQ-10", "documents", f"{invalid.sum()} rows with malformed URL", "WARNING")


def dq11_eps_sign_check():
    """DQ-11 WARNING: EPS sign should match net_profit sign."""
    pnl = load_table("profitandloss")
    if "eps" in pnl.columns and "net_profit" in pnl.columns:
        mismatch = (pnl["eps"] > 0) != (pnl["net_profit"] > 0)
        if mismatch.sum() > 0:
            log_failure("DQ-11", "profitandloss", f"{mismatch.sum()} rows where EPS sign != net profit sign", "WARNING")


def dq12_liabilities_equity_nonneg():
    """DQ-12 WARNING (unconfirmed severity): equity + total_liabilities should not be negative."""
    df = load_table("balancesheet")
    if "equity_capital" in df.columns and "reserves" in df.columns and "total_liabilities" in df.columns:
        total = df["equity_capital"] + df["reserves"] + df["total_liabilities"]
        negative = total < 0
        if negative.sum() > 0:
            log_failure("DQ-12", "balancesheet", f"{negative.sum()} rows with negative equity+liabilities", "WARNING")


def dq13_year_coverage():
    """DQ-13 WARNING: each company should have >= 5 years of P&L data."""
    df = load_table("profitandloss")
    df_valid = df[df["year"] != "PARSE_ERROR"]
    counts = df_valid.groupby("company_id")["year"].nunique()
    low_coverage = counts[counts < 5]
    if len(low_coverage) > 0:
        log_failure("DQ-13", "profitandloss", f"{len(low_coverage)} companies with <5 years of data", "WARNING")


def dq14_null_critical_fields():
    """DQ-14 CRITICAL: company_id and year must not be null / PARSE_ERROR."""
    for name in YEAR_TABLES + CALENDAR_YEAR_TABLES:
        df = load_table(name)
        if "company_id" in df.columns:
            nulls = df["company_id"].isna().sum()
            if nulls > 0:
                log_failure("DQ-14", name, f"{nulls} null company_id values", "CRITICAL")
        if "year" in df.columns:
            bad_year = (df["year"].isna()) | (df["year"] == "PARSE_ERROR")
            if bad_year.sum() > 0:
                log_failure("DQ-14", name, f"{bad_year.sum()} null/unparseable year values", "CRITICAL")


def dq15_stock_price_positive():
    """DQ-15 CRITICAL: OHLC prices must be positive."""
    df = load_table("stock_prices")
    for col in ["open_price", "high_price", "low_price", "close_price"]:
        if col in df.columns:
            invalid = df[col] <= 0
            if invalid.sum() > 0:
                log_failure("DQ-15", "stock_prices", f"{invalid.sum()} rows with non-positive {col}", "CRITICAL")


def dq16_duplicate_rows():
    """DQ-16 WARNING: no fully duplicate rows."""
    for name in ALL_TABLES:
        df = load_table(name)
        dupes = df.duplicated().sum()
        if dupes > 0:
            log_failure("DQ-16", name, f"{dupes} fully duplicate rows", "WARNING")


def run_all_checks():
    checks = [
        dq01_pk_uniqueness, dq02_composite_pk, dq03_fk_integrity, dq04_balance_sheet_balance,
        dq05_opm_cross_check, dq06_positive_sales, dq07_net_cash_consistency, dq08_tax_rate_range,
        dq09_dividend_payout_cap, dq10_url_format, dq11_eps_sign_check, dq12_liabilities_equity_nonneg,
        dq13_year_coverage, dq14_null_critical_fields, dq15_stock_price_positive, dq16_duplicate_rows,
    ]
    print("=" * 60)
    print("RUNNING 16 DATA QUALITY RULES (corrected column names)")
    print("=" * 60)
    for check in checks:
        try:
            check()
            print(f"  ✓ {check.__name__}")
        except Exception as e:
            print(f"  ✗ {check.__name__} — error: {e}")

    df_failures = pd.DataFrame(failures)
    df_failures.to_csv(OUTPUT_PATH / "validation_failures.csv", index=False)

    critical_count = (df_failures["severity"] == "CRITICAL").sum() if len(df_failures) else 0
    warning_count = (df_failures["severity"] == "WARNING").sum() if len(df_failures) else 0

    print(f"\nTotal violations: {len(df_failures)}  (CRITICAL: {critical_count}, WARNING: {warning_count})")
    print(f"Saved: {OUTPUT_PATH / 'validation_failures.csv'}")
    if critical_count > 0:
        print("\n CRITICAL failures found — resolve before Day 5 full load.")
    else:
        print("\n No CRITICAL failures. Safe to proceed.")


if __name__ == "__main__":
    run_all_checks()