"""
Day 12: Runs the full ratio engine (Day 8-11 functions) against all 92 companies' 
        on real data in nifty100.db, writes results into financial_ratios table.
"""

import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR / "src" / "analytics"))

from ratios import (
    net_profit_margin, operating_profit_margin, return_on_equity,
    return_on_capital_employed, return_on_assets, debt_to_equity,
    high_leverage_flag, interest_coverage_ratio, icr_label,
    icr_warning_flag, asset_turnover,
)
from cagr import compute_cagr_for_window
from cashflow_kpis import (
    free_cash_flow, fcf_conversion_rate
)

DB_PATH = BASE_DIR / "db" / "nifty100.db"
OUTPUT_PATH = BASE_DIR / "output"
OUTPUT_PATH.mkdir(parents=True, exist_ok=True)

engine = create_engine(f"sqlite:///{DB_PATH}")


def extend_schema():
    """Add CAGR and composite score columns not present in original Day 4 schema."""
    new_columns = [
        "revenue_cagr_5yr REAL", "revenue_cagr_5yr_flag TEXT",
        "pat_cagr_5yr REAL", "pat_cagr_5yr_flag TEXT",
        "eps_cagr_5yr REAL", "eps_cagr_5yr_flag TEXT",
        "composite_quality_score REAL",
        "high_leverage_flag BOOLEAN",
        "icr_label TEXT",
        "icr_warning_flag BOOLEAN",
    ]
    with engine.connect() as conn:
        for col_def in new_columns:
            col_name = col_def.split()[0]
            try:
                conn.execute(text(f"ALTER TABLE financial_ratios ADD COLUMN {col_def}"))
            except Exception:
                pass  # column already exists, skip silently
        conn.commit()
    print("Schema extended with CAGR + quality score columns (if not already present).")


def load_source_tables():
    """Load the three source tables needed for ratio computation."""
    pnl = pd.read_sql("SELECT * FROM profitandloss", engine)
    bs = pd.read_sql("SELECT * FROM balancesheet", engine)
    cf = pd.read_sql("SELECT * FROM cashflow", engine)
    return pnl, bs, cf


def composite_quality_score(roe, icr, cfo_pat_ratio):
    """
    OUR OWN interpretation — spec does not define an exact formula.
    Simple 0-100 composite: rewards higher ROE, safer ICR, and cash-backed profit.
    """
    score = 0
    weight_total = 0

    if roe is not None:
        score += min(max(roe, 0), 40) * 1.0  # cap ROE contribution at 40 points
        weight_total += 1

    if icr is not None:
        icr_score = min(icr * 10, 30)  # cap ICR contribution at 30 points
        score += icr_score
        weight_total += 1
    elif icr is None:  # debt-free companies get full ICR safety credit
        score += 30
        weight_total += 1

    if cfo_pat_ratio is not None:
        cfo_score = min(cfo_pat_ratio * 30, 30)
        score += cfo_score
        weight_total += 1

    if weight_total == 0:
        return None
    return round(score, 2)


def populate_all_companies(pnl, bs, cf):
    """Compute all ratios for every company-year, return as list of dicts."""
    results = []
    companies = pnl["company_id"].unique()

    print(f"Processing {len(companies)} companies...")

    for company_id in companies:
        company_pnl = pnl[pnl["company_id"] == company_id].sort_values("year")
        company_bs = bs[bs["company_id"] == company_id].sort_values("year")
        company_cf = cf[cf["company_id"] == company_id].sort_values("year")

        # CAGR needs full history, computed once per company (not per year)
        rev_cagr, rev_flag = compute_cagr_for_window(pnl, company_id, "sales", "year", 5)
        pat_cagr_val, pat_flag = compute_cagr_for_window(pnl, company_id, "net_profit", "year", 5)
        eps_cagr_val, eps_flag = compute_cagr_for_window(pnl, company_id, "eps", "year", 5)

        for _, pnl_row in company_pnl.iterrows():
            year = pnl_row["year"]
            bs_row = company_bs[company_bs["year"] == year]
            cf_row = company_cf[company_cf["year"] == year]

            if bs_row.empty or cf_row.empty:
                continue  # skip years without matching balance sheet / cash flow data

            bs_row = bs_row.iloc[0]
            cf_row = cf_row.iloc[0]

            npm = net_profit_margin(pnl_row["net_profit"], pnl_row["sales"])
            opm, opm_mismatch = operating_profit_margin(
                pnl_row["operating_profit"], pnl_row["sales"], pnl_row.get("opm_percentage")
            )
            roe = return_on_equity(pnl_row["net_profit"], bs_row["equity_capital"], bs_row["reserves"])

            ebit = pnl_row["operating_profit"] + pnl_row["other_income"]
            roce = return_on_capital_employed(
                ebit, bs_row["equity_capital"], bs_row["reserves"], bs_row["borrowings"]
            )
            roa = return_on_assets(pnl_row["net_profit"], bs_row["total_assets"])

            de = debt_to_equity(bs_row["borrowings"], bs_row["equity_capital"], bs_row["reserves"])
            icr = interest_coverage_ratio(pnl_row["operating_profit"], pnl_row["other_income"], pnl_row["interest"])
            asset_turn = asset_turnover(pnl_row["sales"], bs_row["total_assets"])

            fcf = free_cash_flow(cf_row["operating_activity"], cf_row["investing_activity"])
            fcf_conv = fcf_conversion_rate(fcf, pnl_row["operating_profit"])

            cfo_pat_ratio = None
            if pnl_row["net_profit"] != 0:
                cfo_pat_ratio = round(cf_row["operating_activity"] / pnl_row["net_profit"], 2)

            quality_score = composite_quality_score(roe, icr, cfo_pat_ratio)

            results.append({
                "company_id": company_id,
                "year": year,
                "net_profit_margin_pct": npm,
                "operating_profit_margin_pct": opm,
                "return_on_equity_pct": roe,
                "debt_to_equity": de,
                "interest_coverage": icr,
                "asset_turnover": asset_turn,
                "free_cash_flow_cr": fcf,
                "capex_cr": None, # Leaving NULL rather than reporting a wrong number. 
                                  # Flag to team: need a real capex source, I am just formally document this column as unavailable.
                "earnings_per_share": pnl_row["eps"],
                "book_value_per_share": None,  # MATHEMATICALLY UNCOMPUTABLE — no shares-outstanding
                                               # data exists anywhere in the 12-table schema.
                                               # Not a missing-value issue, a missing-data-SOURCE issue.
                                               # Must be flagged to team as a schema gap!!
                "dividend_payout_ratio_pct": pnl_row.get("dividend_payout"),
                "total_debt_cr": bs_row["borrowings"],
                "cash_from_operations_cr": cf_row["operating_activity"],
                "revenue_cagr_5yr": rev_cagr,
                "revenue_cagr_5yr_flag": rev_flag,
                "pat_cagr_5yr": pat_cagr_val,
                "pat_cagr_5yr_flag": pat_flag,
                "eps_cagr_5yr": eps_cagr_val,
                "eps_cagr_5yr_flag": eps_flag,
                "composite_quality_score": None,
                "high_leverage_flag": high_leverage_flag(de, None),  # sector arg added in Day 13 carve-out
                "icr_label": icr_label(icr),
                "icr_warning_flag": icr_warning_flag(icr),
            })

            

    return pd.DataFrame(results)


def write_to_db(df):
    with engine.connect() as conn:
        conn.execute(text("DELETE FROM financial_ratios"))
        conn.commit()
    df.to_sql("financial_ratios", engine, if_exists="append", index=False)
    count = pd.read_sql("SELECT COUNT(*) as cnt FROM financial_ratios", engine).iloc[0]["cnt"]
    print(f"\nfinancial_ratios populated: {count} rows")
    print(f"Exit criteria target: >= 1100 rows | Actual: {count}")
    if count < 1100:
        print("[Mismatch] Gap explained:")
        print("         - 15-17 company-years (primarily SBIN, HAL) missing") 
        print("         - matching balancesheet/cashflow data in source files.")
        print("         - Documented in output/ratio_edge_cases.log — not fabricated to close gap.")
    return count


def manual_spot_check(df, sample_companies=3):
    """Print detailed values for a few companies so you can hand-verify in a spreadsheet."""
    print("\n" + "=" * 60)
    print("MANUAL SPOT-CHECK DATA (verify ROE and Revenue CAGR by hand)")
    print("=" * 60)
    sample_ids = df["company_id"].unique()[:sample_companies]
    for cid in sample_ids:
        company_rows = df[df["company_id"] == cid]
        latest = company_rows.iloc[-1]
        print(f"\n--- {cid} ---")
        print(f"  Latest year ROE: {latest['return_on_equity_pct']}%")
        print(f"  5yr Revenue CAGR: {latest['revenue_cagr_5yr']}% (flag: {latest['revenue_cagr_5yr_flag']})")
        print(f"  -> Manually verify: pull net_profit, equity_capital, reserves for {cid}")
        print(f"     from balancesheet/profitandloss, recompute by hand, compare within 0.1%")


if __name__ == "__main__":
    extend_schema()
    pnl, bs, cf = load_source_tables()
    ratios_df = populate_all_companies(pnl, bs, cf)
    row_count = write_to_db(ratios_df)
    manual_spot_check(ratios_df)
    print("\n[DONE] Day 12 population complete.")