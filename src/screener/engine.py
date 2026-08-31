"""
Day 15: Generic filter engine — 
loads screener_config.yaml, applies any combination of threshold filters to the financial_ratios universe...
"""

import pandas as pd
import yaml
from pathlib import Path
from sqlalchemy import create_engine

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "db" / "nifty100.db"
CONFIG_PATH = BASE_DIR / "src" / "screener" / "screener_config.yaml"

db_engine = create_engine(f"sqlite:///{DB_PATH}")


def load_config():
    """Load filter definitions from the analyst-editable YAML config."""
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)


def load_universe():
    """
    Load the full screening universe: 
    financial_ratios joined with sectors(needed for the Financials D/E skip rule) 
    and market_cap/financial data (needed for P/E, P/B, dividend yield filters not present in financial_ratios).
    - Then it merges them all into one wide table...
    """
    ratios = pd.read_sql("SELECT * FROM financial_ratios", db_engine)
    sectors = pd.read_sql("SELECT company_id, broad_sector FROM sectors", db_engine)
    market_cap = pd.read_sql(
        "SELECT company_id, year, market_cap_crore, pe_ratio, pb_ratio, dividend_yield_pct FROM market_cap",
        db_engine
    )
    pnl = pd.read_sql("SELECT company_id, year, sales, net_profit FROM profitandloss", db_engine)

    # Use each company's latest year only for screening (a snapshot view, not full history)
    ratios_latest = ratios.sort_values("year").groupby("company_id").last().reset_index()
    market_cap_latest = market_cap.sort_values("year").groupby("company_id").last().reset_index()  
    pnl_latest = pnl.sort_values("year").groupby("company_id").last().reset_index()                  

    df = ratios_latest.merge(sectors, on="company_id", how="left")
    df = df.merge(market_cap_latest, on="company_id", how="left", suffixes=("", "_mc"))   # use _latest version
    df = df.merge(pnl_latest, on="company_id", how="left", suffixes=("", "_pnl"))          # use _latest version

    return df



def apply_icr_infinity_rule(df, icr_col="interest_coverage", icr_label_col="icr_label"):
    """
    Per spec: ICR = None with icr_label = 'Debt Free' should be treated as
    ICR = infinity for filtering purposes -- a debt-free company always
    passes ANY minimum ICR threshold, since it has no interest burden at all.
    We use a very large number (1e9) as a practical stand-in for infinity,
    since actual infinity would break numeric comparisons in pandas.
    """
    df = df.copy()
    debt_free_mask = df[icr_label_col] == "Debt Free"
    df.loc[debt_free_mask, icr_col] = 1e9
    return df


def apply_filter(df, filter_name, threshold, config):
    """
    Applies a single named filter (e.g., 'roe_min') at the given threshold
    to the DataFrame, returning the filtered subset.
    """
    filter_def = config["filters"].get(filter_name)
    if filter_def is None:
        raise ValueError(f"Unknown filter: {filter_name}")

    column = filter_def["column"]
    direction = filter_def["direction"]
    skip_sector = filter_def.get("skip_sector")

    working_df = df.copy()

    # Special case: ICR infinity rule for Debt Free companies
    if filter_name == "icr_min":
        working_df = apply_icr_infinity_rule(working_df)

    # Special case: D/E filter skips Financials sector entirely (they pass automatically)
    if skip_sector:
        exempt = working_df["broad_sector"] == skip_sector
        subject_to_filter = working_df[~exempt]
        exempt_rows = working_df[exempt]

        if direction == "min":
            passed = subject_to_filter[subject_to_filter[column] >= threshold]
        else:
            passed = subject_to_filter[subject_to_filter[column] <= threshold]

        return pd.concat([passed, exempt_rows], ignore_index=True)

    # Standard case: normal min/max threshold filter
    if direction == "min":
        return working_df[working_df[column] >= threshold]
    else:
        return working_df[working_df[column] <= threshold]


def run_screener(filters_dict):
    """
    Runs multiple filters together (AND logic — a company must pass ALL
    given filters to remain in the result).

    filters_dict: {"roe_min": 15, "de_max": 1.0, ...}

    Returns the filtered DataFrame, sorted by composite_quality_score
    descending (column added here as a placeholder; real scoring logic
    is built in Day 17 -- for now this just ensures the column exists
    so downstream code doesn't break on a missing column).
    """
    config = load_config()
    df = load_universe()

    if "composite_quality_score" not in df.columns:
        df["composite_quality_score"] = None  # placeholder until Day 17

    for filter_name, threshold in filters_dict.items():
        df = apply_filter(df, filter_name, threshold, config)

    return df.sort_values("composite_quality_score", ascending=False, na_position="last")


if __name__ == "__main__":
    # Quick smoke test: ROE > 15%, D/E < 1
    result = run_screener({"roe_min": 15, "de_max": 1.0})
    print(f"Companies matching ROE>15%, D/E<1: {len(result)}")
    print(result[["company_id", "return_on_equity_pct", "debt_to_equity", "broad_sector"]].head(10))