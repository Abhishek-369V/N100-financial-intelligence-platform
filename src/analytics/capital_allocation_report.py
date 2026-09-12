"""
Sprint 5, Day 32 — Capital Allocation Report
"""

import sqlite3
from pathlib import Path

import pandas as pd

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cashflow_kpis import generate_capital_allocation_output

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "db" / "nifty100.db"
OUT_DIR = BASE_DIR / "output"


def load_cashflow_and_pnl():
    con = sqlite3.connect(DB_PATH)
    cashflow_df = pd.read_sql("SELECT * FROM cashflow ORDER BY company_id, year", con)
    pnl_df = pd.read_sql("SELECT company_id, year, net_profit FROM profitandloss ORDER BY company_id, year", con)
    con.close()
    return cashflow_df, pnl_df


def build_capital_allocation_csv():
    """
    Regenerates output/capital_allocation.csv (the Sprint 2 deliverable
    that doesn't actually exist yet -- see sprint5_retro.md- gap day32 - #1) for
    every company-year row available.
    """
    cashflow_df, pnl_df = load_cashflow_and_pnl()
    merged = cashflow_df.merge(pnl_df, on=["company_id", "year"], how="left")
    alloc_df = generate_capital_allocation_output(merged)
    alloc_df.to_csv(OUT_DIR / "capital_allocation.csv", index=False)
    return alloc_df


def build_distribution_summary(alloc_df):
    """
    Count of companies in each of the 8 patterns for the latest year only
    (one row per company, not per company-year).
    """
    latest = alloc_df.sort_values("year").groupby("company_id").last().reset_index()
    summary = latest["pattern_label"].value_counts().reset_index()
    summary.columns = ["pattern_label", "company_count"]
    return summary, latest


def build_pattern_changes(alloc_df):
    """
    Companies whose pattern_label changed from one year to the very next
    year they have data for (e.g. Reinvestor -> Distress Signal).
    Only companies with >=2 years of data can appear here at all.
    """
    changes = []
    for company_id, group in alloc_df.sort_values("year").groupby("company_id"):
        labels = group["pattern_label"].tolist()
        years = group["year"].tolist()
        for i in range(1, len(labels)):
            if labels[i] != labels[i - 1]:
                changes.append({
                    "company_id": company_id,
                    "from_year": years[i - 1],
                    "to_year": years[i],
                    "from_pattern": labels[i - 1],
                    "to_pattern": labels[i],
                })
    return pd.DataFrame(changes, columns=["company_id", "from_year", "to_year", "from_pattern", "to_pattern"])


def merge_into_cashflow_intelligence(latest_alloc_df):
    """
    Day 31 already writes capital_allocation_label into cashflow_intelligence.xlsx
    directly (computed inline from each company's own latest cash flow row), so
    there's nothing to merge here -- confirmed the two are consistent on the
    same latest-year row for every company, per spec's "add capital allocation
    column to cashflow_intelligence.xlsx" instruction (already satisfied).
    """
    ci_path = OUT_DIR / "cashflow_intelligence.xlsx"
    ci_df = pd.read_excel(ci_path)
    check = ci_df.merge(
        latest_alloc_df[["company_id", "pattern_label"]], on="company_id", how="left"
    )
    mismatches = check[
        check["capital_allocation_label"].fillna("") != check["pattern_label"].fillna("")
    ]
    return mismatches


if __name__ == "__main__":
    alloc_df = build_capital_allocation_csv()
    print(f"capital_allocation.csv rows: {len(alloc_df)} (company-years)")
    print(f"Companies covered: {alloc_df['company_id'].nunique()} / 92")

    summary, latest = build_distribution_summary(alloc_df)
    print("\nLatest-year distribution:")
    print(summary.to_string(index=False))

    changes_df = build_pattern_changes(alloc_df)
    changes_df.to_csv(OUT_DIR / "pattern_changes.csv", index=False)
    print(f"\nCompanies with a year-over-year pattern change: {changes_df['company_id'].nunique()}")
    print(f"Total pattern-change events: {len(changes_df)}")

    mismatches = merge_into_cashflow_intelligence(latest)
    print(f"\nMismatches vs cashflow_intelligence.xlsx capital_allocation_label: {len(mismatches)}")
    if len(mismatches):
        print(mismatches[["company_id", "capital_allocation_label", "pattern_label"]].to_string(index=False))