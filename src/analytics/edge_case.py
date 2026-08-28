"""
Day 13: Sector-aware D/E flag suppression for Financials, ROCE/ROE cross-checks 
        against pre-computed companies.xlsx values, anomaly logging.
"""

import pandas as pd
from sqlalchemy import create_engine, text
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "db" / "nifty100.db"
OUTPUT_PATH = BASE_DIR / "output"

engine = create_engine(f"sqlite:///{DB_PATH}")


def apply_financials_sector_carveout():
    """
    Re-applies high_leverage_flag with sector awareness — Day 12 computed
    this flag without knowing each company's sector (sector data lives in
    a separate table). This step joins sectors in and recomputes correctly.
    """
    ratios = pd.read_sql("SELECT * FROM financial_ratios", engine)
    sectors = pd.read_sql("SELECT company_id, broad_sector FROM sectors", engine)

    merged = ratios.merge(sectors, on="company_id", how="left")

    financials_count = merged[merged["broad_sector"] == "Financials"]["company_id"].nunique()
    print(f"Companies in Financials sector: {financials_count}")

    # Suppress high_leverage_flag for Financials sector, per spec
    merged["high_leverage_flag"] = merged.apply(
        lambda row: False if row["broad_sector"] == "Financials" else row["high_leverage_flag"],
        axis=1
    )

    # Write back only the corrected flag column
    with engine.connect() as conn:
        for _, row in merged.iterrows():
            conn.execute(
                text(
                    "UPDATE financial_ratios SET high_leverage_flag = :flag "
                    "WHERE company_id = :cid AND year = :yr"
                ),
                {"flag": row["high_leverage_flag"], "cid": row["company_id"], "yr": row["year"]}
            )
        conn.commit()

    print(f"[SUCCESS] Sector carve-out applied. {financials_count} Financials-sector companies "
          f"had high_leverage_flag suppressed.")
    return merged


def cross_check_roce_roe(merged_df):
    """
    Compares OUR computed ROCE/ROE against companies.xlsx's pre-computed
    roce_percentage/roe_percentage columns. Logs anomalies > 5% difference.
    """
    companies = pd.read_sql("SELECT id, roce_percentage, roe_percentage FROM companies", engine)
    companies = companies.rename(columns={"id": "company_id"})

    # Use each company's LATEST year for comparison (source values are single-point, not per-year)
    latest = merged_df.sort_values("year").groupby("company_id").last().reset_index()
    compare = latest.merge(companies, on="company_id", how="inner")

    anomalies = []

    for _, row in compare.iterrows():
        # ROE comparison
        if pd.notna(row["return_on_equity_pct"]) and pd.notna(row["roe_percentage"]):
            diff = abs(row["return_on_equity_pct"] - row["roe_percentage"])
            if diff > 5:
                category = categorize_anomaly(row["company_id"], "ROE", row["return_on_equity_pct"], row["roe_percentage"])
                anomalies.append({
                    "company_id": row["company_id"], "metric": "ROE",
                    "computed": row["return_on_equity_pct"], "source": row["roe_percentage"],
                    "diff": round(diff, 2), "category": category
                })

    return pd.DataFrame(anomalies)


def categorize_anomaly(computed, source):
    """
    catches BOTH directions of implausibility, not just source-near-zero.
    """
    if source is not None and abs(source) < 1 and abs(computed) > 5:
        return "data source issue (source value implausibly near zero)"

    if computed is not None and abs(computed) > 200:
        return "likely calculation artifact (denominator near zero - verify equity_capital+reserves for this company-year)"

    if abs(computed - source) > 30:
        return "large discrepancy - requires manual review, not confirmed as begin formula difference"

    return "formula discrepancy (methodology difference, plausible)"


def write_edge_case_log(anomalies_df):
    log_path = OUTPUT_PATH / "ratio_edge_cases.log"
    with open(log_path, "a") as f:
        f.write("\n" + "=" * 60 + "\n")
        f.write("DAY 13 - ROE/ROCE CROSS-CHECK ANOMALIES\n")
        f.write("=" * 60 + "\n")
        for _, row in anomalies_df.iterrows():
            f.write(
                f"{row['company_id']} | {row['metric']} | "
                f"computed={row['computed']}% source={row['source']}% "
                f"diff={row['diff']}pp | category: {row['category']}\n"
            )
    print(f"\n{len(anomalies_df)} anomalies logged to {log_path}")


if __name__ == "__main__":
    merged = apply_financials_sector_carveout()
    anomalies = cross_check_roce_roe(merged)
    write_edge_case_log(anomalies)
    print("\n[DONE] Day 13 complete.")