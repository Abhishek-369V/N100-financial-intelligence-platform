"""
Day 26 — Valuation Module.

ASSUMPTION FLAGGED: spec says "using market_cap.xlsx data". Reading the loaded db.market_cap table 
instead of the raw data/processed/market_cap.csv (the xlsx's post-loader intermediate) 
-- same as every other analytics module in this project (peer.py, composite_score.py, cashflow_kpis.py all
read from the DB, never the raw files directly).
Going around the loader
would reintroduce the exact orphan/duplicate/TTM-year issues Sprint 1 already found and fixed.

Sector median P/E and the Caution/Discount/Fair 
flag both use each company's LATEST year P/E vs its sector's LATEST year median P/E 
-- not the 5yr median (that's a separate reference column per spec's own column list, not part of the flag formula as worded).
"""

import pandas as pd
from pathlib import Path
from sqlalchemy import create_engine

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "db" / "nifty100.db"
OUTPUT_PATH = BASE_DIR / "output"
OUTPUT_PATH.mkdir(parents=True, exist_ok=True)

db_engine = create_engine(f"sqlite:///{DB_PATH}")


def load_data():
    market_cap = pd.read_sql("SELECT * FROM market_cap", db_engine)
    ratios = pd.read_sql(
        "SELECT company_id, year, free_cash_flow_cr FROM financial_ratios", db_engine
    )
    companies = pd.read_sql("SELECT id AS company_id, company_name FROM companies", db_engine)
    sectors = pd.read_sql("SELECT company_id, broad_sector FROM sectors", db_engine)
    return market_cap, ratios, companies, sectors


def latest_year_rows(df, value_cols):
    """Each company's most recent year's row, for the given value columns."""
    cols = ["company_id", "year"] + value_cols
    return df[cols].sort_values("year").groupby("company_id").last().reset_index()


def compute_fcf_yield(latest_mc, latest_fcf):
    """FCF yield % = FCF / market_cap_crore * 100."""
    merged = latest_mc.merge(latest_fcf, on="company_id", how="left")
    merged["fcf_yield_pct"] = (merged["free_cash_flow_cr"] / merged["market_cap_crore"]) * 100
    return merged


def compute_5yr_median_pe(market_cap):
    """Each company's own trailing 5-year median P/E (reference column, not used in the flag)."""
    result = {}
    for company_id, group in market_cap.groupby("company_id"):
        last5 = group.sort_values("year").tail(5)
        result[company_id] = last5["pe_ratio"].median()
    return pd.Series(result, name="pe_5yr_median")


def compute_sector_median_pe(latest_mc, sectors):
    """Sector median P/E in the latest year, per broad_sector."""
    merged = latest_mc.merge(sectors, on="company_id", how="left")
    medians = merged.groupby("broad_sector")["pe_ratio"].median()
    return medians


def apply_valuation_flag(row):
    if pd.isna(row["pe_ratio"]) or pd.isna(row["sector_median_pe"]) or row["sector_median_pe"] == 0:
        return None
    if row["pe_ratio"] > row["sector_median_pe"] * 1.5:
        return "Caution"
    if row["pe_ratio"] < row["sector_median_pe"] * 0.7:
        return "Discount"
    return "Fair"


def generate_valuation_summary():
    market_cap, ratios, companies, sectors = load_data()

    latest_mc = latest_year_rows(
        market_cap, ["market_cap_crore", "pe_ratio", "pb_ratio", "ev_ebitda"]
    )
    latest_fcf = latest_year_rows(ratios, ["free_cash_flow_cr"])[["company_id", "free_cash_flow_cr"]]

    summary = compute_fcf_yield(latest_mc, latest_fcf)

    pe_5yr = compute_5yr_median_pe(market_cap)
    summary = summary.merge(pe_5yr.rename("pe_5yr_median"), left_on="company_id", right_index=True, how="left")

    summary = summary.merge(sectors, on="company_id", how="left")
    sector_medians = compute_sector_median_pe(latest_mc, sectors)
    summary["sector_median_pe"] = summary["broad_sector"].map(sector_medians)

    summary["pe_vs_sector_median_pct"] = (
        (summary["pe_ratio"] - summary["sector_median_pe"]) / summary["sector_median_pe"] * 100
    )
    summary["flag"] = summary.apply(apply_valuation_flag, axis=1)

    summary = summary.merge(companies, on="company_id", how="left")

    summary = summary.rename(columns={
        "broad_sector": "sector",
        "pe_ratio": "P/E",
        "pb_ratio": "P/B",
        "ev_ebitda": "EV/EBITDA",
    })

    final_cols = [
        "company_id", "company_name", "sector", "P/E", "P/B", "EV/EBITDA",
        "fcf_yield_pct", "pe_5yr_median", "pe_vs_sector_median_pct", "flag",
    ]
    summary = summary[final_cols]

    output_file = OUTPUT_PATH / "valuation_summary.xlsx"
    summary.to_excel(output_file, index=False)

    flagged = summary[summary["flag"].isin(["Caution", "Discount"])].sort_values("flag")
    flags_file = OUTPUT_PATH / "valuation_flags.csv"
    flagged.to_csv(flags_file, index=False)

    print(f"Total companies: {len(summary)} (expect 92)")
    print(f"Missing P/E: {summary['P/E'].isna().sum()}")
    print(f"Flag counts:\n{summary['flag'].value_counts(dropna=False)}")
    print(f"valuation_flags.csv rows: {len(flagged)}")

    return summary, flagged


if __name__ == "__main__":
    generate_valuation_summary()