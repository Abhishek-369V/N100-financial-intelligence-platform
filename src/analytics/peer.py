"""
Day 18(SPRINT3): Peer percentile rankings — computes PERCENT_RANK for 10 metrics
                within each of 11 peer groups, writes to peer_percentiles table.
"""

import pandas as pd
from pathlib import Path
from sqlalchemy import create_engine, text

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "db" / "nifty100.db"

db_engine = create_engine(f"sqlite:///{DB_PATH}")

# The 10 metrics required by spec, and whether lower or higher is "better"
# (determines whether we invert the percentile rank)
PEER_METRICS = {
    "return_on_equity_pct": "higher_better",
    "roce_percentage": "higher_better",
    "net_profit_margin_pct": "higher_better",
    "debt_to_equity": "lower_better",          # inverted per spec
    "free_cash_flow_cr": "higher_better",
    "pat_cagr_5yr": "higher_better",
    "revenue_cagr_5yr": "higher_better",
    "eps_cagr_5yr": "higher_better",
    "interest_coverage": "higher_better",
    "asset_turnover": "higher_better",
}


def load_peer_groups_and_ratios():
    """
    Loads peer_groups (which company belongs to which named group) and 
    financial_ratios (latest year per company, same 'snapshot' pattern used since Day 15's screener engine).
    """
    peer_groups = pd.read_sql("SELECT peer_group_name, company_id, is_benchmark FROM peer_groups", db_engine)
    ratios = pd.read_sql("SELECT * FROM financial_ratios", db_engine)
    companies = pd.read_sql("SELECT id as company_id, roce_percentage FROM companies", db_engine)

    ratios_latest = ratios.sort_values("year").groupby("company_id").last().reset_index()
    ratios_latest = ratios_latest.merge(companies, on="company_id", how="left")

    return peer_groups, ratios_latest


def compute_percentile_ranks(peer_groups, ratios):
    """
    For each peer group, for each of the 10 metrics, 
    computes each member company's percentile rank RELATIVE TO ONLY THAT GROUP 
    (not the full 92-company universe -- this is the key difference from every previous day's scoring).
    """
    merged = peer_groups.merge(ratios, on="company_id", how="left")

    results = []
    groups_with_no_data = []

    for group_name, group_df in merged.groupby("peer_group_name"):
        if len(group_df) < 2:
            # Can't meaningfully rank a "group" of 1 -- percentile rank
            # is undefined/meaningless with a single member.
            groups_with_no_data.append(group_name)
            continue

        for metric, direction in PEER_METRICS.items():
            if metric not in group_df.columns:
                continue

            valid = group_df.dropna(subset=[metric])
            if len(valid) < 2:
                continue

            ranks = valid[metric].rank(pct=True, method="average")

            if direction == "lower_better":
                ranks = 1 - ranks  # spec's inversion rule for D/E

            for idx, company_id in valid["company_id"].items():
                results.append({
                    "company_id": company_id,
                    "peer_group_name": group_name,
                    "metric": metric,
                    "value": valid.loc[idx, metric],
                    "percentile_rank": round(ranks.loc[idx], 4),
                    "year": valid.loc[idx, "year"] if "year" in valid.columns else None,
                })

    if groups_with_no_data:
        print(f"[WARNING]  Groups with insufficient members to rank: {groups_with_no_data}")

    return pd.DataFrame(results)


def flag_companies_without_peer_group(peer_groups, ratios):
    """
    Per spec: companies with NO peer group assignment should return a message, not raise an error. 
    Identifies which of the 92 companies aren't in any peer_groups row at all.
    """
    all_companies = set(ratios["company_id"].unique())
    grouped_companies = set(peer_groups["company_id"].unique())
    ungrouped = all_companies - grouped_companies

    if ungrouped:
        print(f"\nNo peer group assigned for {len(ungrouped)} companies: {sorted(ungrouped)}")
    else:
        print("\nAll companies have a peer group assignment.")

    return ungrouped


def write_peer_percentiles_table(df):
    df.to_sql("peer_percentiles", db_engine, if_exists="replace", index=False)
    count = pd.read_sql("SELECT COUNT(*) as cnt FROM peer_percentiles", db_engine).iloc[0]["cnt"]
    print(f"\npeer_percentiles table populated: {count} rows")
    return count


# Quick Smoke Test!...
if __name__ == "__main__":
    peer_groups, ratios = load_peer_groups_and_ratios()

    print(f"Peer groups found: {peer_groups['peer_group_name'].nunique()}")
    print(f"Expected: 11 (per spec)")

    ungrouped = flag_companies_without_peer_group(peer_groups, ratios)

    percentiles = compute_percentile_ranks(peer_groups, ratios)
    write_peer_percentiles_table(percentiles)

    print("\n" + "=" * 60)
    print("SPOT CHECK — IT Services peer group, ROE percentile ranks")
    print("=" * 60)
    it_check = percentiles[
    (percentiles["peer_group_name"] == "IT Services") &   # exact match, not .str.contains
    (percentiles["metric"] == "return_on_equity_pct")].sort_values("percentile_rank", ascending=False)
    print(it_check[["company_id", "value", "percentile_rank"]])

    print()
    peer_groups, ratios = load_peer_groups_and_ratios() 
    print(sorted(peer_groups["peer_group_name"].unique()))

    print()
    print("Total rows in peer_groups.xlsx-derived table:", len(peer_groups))
    print("Unique companies referenced in peer_groups:", peer_groups["company_id"].nunique())