"""
manual_review.py — N100 Financial Intelligence Platform
Day 6: Manual review of 5 random companies, year coverage check,
flag companies with <5 years of P&L data.
"""

import pandas as pd
from pathlib import Path
from sqlalchemy import create_engine

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "db" / "nifty100.db"
OUTPUT_PATH = BASE_DIR / "output"

engine = create_engine(f"sqlite:///{DB_PATH}")


def sample_five_companies(seed=42):
    """Pick 5 random companies and print their full profile for manual eyeball review."""
    companies = pd.read_sql("SELECT * FROM companies", engine)
    sample = companies.sample(n=5, random_state=seed)

    print("=" * 60)
    print("MANUAL REVIEW — 5 RANDOM COMPANIES")
    print("=" * 60)

    for _, row in sample.iterrows():
        cid = row["id"]
        print(f"\n--- {cid} ({row['company_name']}) ---")

        pnl = pd.read_sql(f"SELECT year, sales, net_profit FROM profitandloss WHERE company_id = '{cid}' ORDER BY year", engine)
        print(f"  P&L rows: {len(pnl)}  |  years: {pnl['year'].tolist()}")

        bs = pd.read_sql(f"SELECT COUNT(*) as cnt FROM balancesheet WHERE company_id = '{cid}'", engine)
        print(f"  Balance sheet rows: {bs.iloc[0]['cnt']}")

        cf = pd.read_sql(f"SELECT COUNT(*) as cnt FROM cashflow WHERE company_id = '{cid}'", engine)
        print(f"  Cash flow rows: {cf.iloc[0]['cnt']}")

        sector = pd.read_sql(f"SELECT broad_sector, sub_sector FROM sectors WHERE company_id = '{cid}'", engine)
        if len(sector) > 0:
            print(f"  Sector: {sector.iloc[0]['broad_sector']} / {sector.iloc[0]['sub_sector']}")

    return sample


def year_coverage_report():
    """Companies with fewer than 5 years of P&L data — flagged for review."""
    pnl = pd.read_sql("SELECT company_id, year FROM profitandloss", engine)
    coverage = pnl.groupby("company_id")["year"].nunique().reset_index()
    coverage.columns = ["company_id", "years_covered"]

    low_coverage = coverage[coverage["years_covered"] < 5].sort_values("years_covered")

    print("\n" + "=" * 60)
    print("YEAR COVERAGE REPORT")
    print("=" * 60)
    print(f"Total companies with P&L data: {len(coverage)}")
    print(f"Companies with <5 years coverage: {len(low_coverage)}")
    if len(low_coverage) > 0:
        print(low_coverage.to_string(index=False))

    coverage.to_csv(OUTPUT_PATH / "year_coverage_report.csv", index=False)
    print(f"\nSaved: {OUTPUT_PATH / 'year_coverage_report.csv'}")
    return low_coverage


def orphan_and_duplicate_summary():
    """Re-confirm Day 3 findings are correctly excluded post-load."""
    print("\n" + "=" * 60)
    print("POST-LOAD SANITY CHECK — Day 3 findings resolved?")
    print("=" * 60)

    companies = pd.read_sql("SELECT id FROM companies", engine)
    valid_ids = set(companies["id"])

    for table in ["profitandloss", "balancesheet", "cashflow"]:
        df = pd.read_sql(f"SELECT company_id, year FROM {table}", engine)
        orphans = (~df["company_id"].isin(valid_ids)).sum()
        dupes = df.duplicated(subset=["company_id", "year"]).sum()
        status = "[DONE]" if orphans == 0 and dupes == 0 else "[ERROR]"
        print(f"  {status} {table}: {orphans} orphans, {dupes} duplicate pairs remaining in DB")


if __name__ == "__main__":
    sample_five_companies()
    year_coverage_report()
    orphan_and_duplicate_summary()
    print("\n --> Day 6 manual review complete.")


# Findings:
# DATA QUALITY NOTE: 
# 1. DEFECT: 
#    - companies.xlsx row for ticker 'ABB' has company_name = "Abbott India Ltd" — incorrect. 
#    - ABB (NSE) = ABB India Ltd (Industrials/Capital Goods).
#    - Abbott India's real ticker is ABBOTINDIA. 
#    - Sector/financial data is correctly aligned to ABB India; only the display name field is mislabeled.
#    - Action: flagged to team via standups
# 2. EXPECTED EXCEPTION:
#    - JIOFIN — 2 years of data flagged, and this is expected, not a bug. 
#    - Jio Financial Services was only demerged/listed in 2023, so it genuinely can't have historical financials 
#      going back further — 2 years of coverage is correct for a company that recently listed.
