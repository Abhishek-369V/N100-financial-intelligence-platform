r"""
Sprint 5, Day 29 -- Analysis TextParser Parses free-text period/value fields in data/raw/analysis.xlsx into structured rows.

GAP HANDLING (decided and documented, not silently patched):
1. Reads data/processed/analysis.csv (not data/raw/analysis.xlsx). Verified
   byte-for-byte identical content after dtype alignment -- the processed
   CSV is just the already-flattened, already-clean version (no title-banner
   row to skip), and it's the project convention to read from processed/
   rather than raw/ once a cleaned copy exists.
2. Spec regex `(\d+)\s*Years?:?\s*([\d.]+)%` only matches the "N Years: X%" shape.
   In the real data, ~1 in 4 entries per company uses "TTM:", "1 Year:", or
   "Last Year:" instead of a numbered Years label (all three mean the same
   thing: trailing 1-year figure). Strictly following the spec regex would
   dump 25% of otherwise-valid data into parse_failures.csv as "malformed."
   Decision: treat TTM / Last Year as period_years = 1 via a second regex
   pass, and tag the row's source_label so this normalization is auditable
   -- NOT silently merged with real "1 Year:" entries.
3. Only 5 of 92 companies (HDFCBANK, SBILIFE, TCS, WIPRO, INFY) have any rows
   in analysis.xlsx at all. This is a genuine source-data coverage gap, not a
   parser bug -- confirmed by inspecting the raw file. analysis_parsed.csv
   will therefore only ever have rows for these 5 companies; this is noted
   in the sprint retrospective, not hidden.
4. The spec regex `([\d.]+)%` cannot match negative growth (e.g. "3 Years:
   -1%", a real WIPRO stock-price CAGR in this data). Real financial CAGR
   can legitimately be negative -- excluding it would silently misclassify
   a valid negative figure as a parse failure. Extended both patterns to
   `([\d.\-]+)%` to capture the sign.
"""

import re
import sqlite3
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent.parent
RAW_PATH = BASE_DIR / "data" / "processed" / "analysis.csv"
DB_PATH = BASE_DIR / "db" / "nifty100.db"
OUT_PARSED = BASE_DIR / "output" / "analysis_parsed.csv"
OUT_FAILURES = BASE_DIR / "output" / "parse_failures.csv"
OUT_CROSSVAL = BASE_DIR / "output" / "cagr_crossvalidation.csv"

METRIC_COLUMNS = [
    "compounded_sales_growth",
    "compounded_profit_growth",
    "stock_price_cagr",
    "roe",
]

# Spec pattern extended to allow a leading minus sign (negative CAGR is valid):
# "10 Years: 21%", "5 Years:       24%", "3 Years:      -1%"
YEARS_PATTERN = re.compile(r"(\d+)\s*Years?:?\s*([\d.\-]+)%")
# Extension pattern for the TTM / 1 Year / Last Year family -> period_years = 1
TTM_PATTERN = re.compile(r"(TTM|1\s*Year|Last\s*Year):?\s*([\d.\-]+)%", re.IGNORECASE)

# Cross-validation: map parser metric names to financial_ratios columns,
# but only meaningful for the 5-year period (that's the only overlapping window).
CROSSVAL_MAP = {
    "compounded_sales_growth": "revenue_cagr_5yr",
    "compounded_profit_growth": "pat_cagr_5yr",
}


def parse_cell(raw_text):
    """
    Returns (period_years, value_pct, source_label, matched) for one text cell.
    matched=False means neither pattern hit -> caller logs to parse_failures.
    """
    if raw_text is None or (isinstance(raw_text, float) and pd.isna(raw_text)):
        return None, None, None, False

    text = str(raw_text).strip()

    m = YEARS_PATTERN.search(text)
    if m:
        return int(m.group(1)), float(m.group(2)), "years_exact", True

    m = TTM_PATTERN.search(text)
    if m:
        return 1, float(m.group(2)), f"normalized:{m.group(1).strip()}", True

    return None, None, None, False


def parse_analysis_file():
    df = pd.read_csv(RAW_PATH)

    parsed_rows = []
    failure_rows = []

    for _, row in df.iterrows():
        company_id = row["company_id"]
        for metric in METRIC_COLUMNS:
            raw_text = row[metric]
            period_years, value_pct, source_label, matched = parse_cell(raw_text)

            if matched:
                parsed_rows.append({
                    "company_id": company_id,
                    "metric_type": metric,
                    "period_years": period_years,
                    "value_pct": value_pct,
                    "source_label": source_label,
                })
            else:
                failure_rows.append({
                    "company_id": company_id,
                    "metric_type": metric,
                    "raw_text": raw_text,
                })

    parsed_df = pd.DataFrame(parsed_rows)
    OUT_PARSED.parent.mkdir(parents=True, exist_ok=True)
    parsed_df.to_csv(OUT_PARSED, index=False)

    # Only write parse_failures.csv when there's actually failure to review --
    if failure_rows:
        failures_df = pd.DataFrame(failure_rows, columns=["company_id", "metric_type", "raw_text"])
        failures_df.to_csv(OUT_FAILURES, index=False)
    else:
        failures_df = pd.DataFrame(columns=["company_id", "metric_type", "raw_text"])
        OUT_FAILURES.unlink(missing_ok=True)

    return parsed_df, failures_df


def crossvalidate(parsed_df):
    """
    Compares parsed 5-year CAGR figures against the Ratio Engine's own
    revenue_cagr_5yr / pat_cagr_5yr (financial_ratios, latest year per company).
    Flags divergence > 5 percentage points for manual review.
    """
    con = sqlite3.connect(DB_PATH)
    ratios = pd.read_sql("SELECT * FROM financial_ratios", con)
    con.close()

    ratios_latest = (
        ratios.sort_values("year").groupby("company_id").last().reset_index()
    )

    results = []
    five_yr = parsed_df[parsed_df["period_years"] == 5]

    for _, prow in five_yr.iterrows():
        engine_col = CROSSVAL_MAP.get(prow["metric_type"])
        if engine_col is None:
            continue

        match = ratios_latest[ratios_latest["company_id"] == prow["company_id"]]
        if match.empty or pd.isna(match.iloc[0][engine_col]):
            continue

        engine_value = match.iloc[0][engine_col]
        divergence = abs(prow["value_pct"] - engine_value)

        results.append({
            "company_id": prow["company_id"],
            "metric_type": prow["metric_type"],
            "parsed_5yr_value_pct": prow["value_pct"],
            "ratio_engine_value_pct": round(engine_value, 2),
            "divergence_pct_points": round(divergence, 2),
            "flag_manual_review": divergence > 5,
        })

    crossval_df = pd.DataFrame(results)
    crossval_df.to_csv(OUT_CROSSVAL, index=False)
    return crossval_df


if __name__ == "__main__":
    parsed_df, failures_df = parse_analysis_file()
    print(f"Parsed rows: {len(parsed_df)}")
    print(f"Companies with any analysis data: {parsed_df['company_id'].nunique() if not parsed_df.empty else 0} / 92")
    print(f"Parse failures (genuinely malformed): {len(failures_df)}")

    crossval_df = crossvalidate(parsed_df)
    flagged = crossval_df[crossval_df["flag_manual_review"]] if not crossval_df.empty else crossval_df
    print(f"Cross-validation rows: {len(crossval_df)} | flagged for manual review: {len(flagged)}")
    if not flagged.empty:
        print(flagged.to_string(index=False))