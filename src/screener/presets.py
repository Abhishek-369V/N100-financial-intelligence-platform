"""
Day 16: 6 preset screener strategies, built on top of Day 15's core Filter Engine.
"""

import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

from engine import load_universe

OUTPUT_PATH = BASE_DIR / "output"
OUTPUT_PATH.mkdir(parents=True, exist_ok=True)

# Sanity bound for flagging (not filtering) extreme values, pending - for Day 17's formal winsorization. 
# A ROE above 200% is implausible for organic operations and almost always signals a near-zero-denominator artifact 
# (see BEL, Day 13 log).
EXTREME_ROE_THRESHOLD = 200


def flag_extreme_values(df):
    """
    Adds a non-destructive warning column -- does NOT remove or alter any
    data. Just marks rows that likely contain a calculation artifact, so
    downstream Excel export (Day 17) and human reviewers can see it clearly
    rather than treating an extreme value as a genuine top performer.
    """
    df = df.copy()
    df["data_quality_flag"] = ""
    if "return_on_equity_pct" in df.columns:
        extreme_mask = df["return_on_equity_pct"].abs() > EXTREME_ROE_THRESHOLD
        df.loc[extreme_mask, "data_quality_flag"] = "EXTREME_ROE_LIKELY_ARTIFACT"
    return df


def quality_compounder():
    """ROE > 15%, D/E < 1.0, FCF > 0, Revenue CAGR 5yr > 10%"""
    df = load_universe()
    df = df[df["return_on_equity_pct"] > 15]
    df = df[df["debt_to_equity"] < 1.0]
    df = df[df["free_cash_flow_cr"] > 0]
    df = df[df["revenue_cagr_5yr"] > 10]
    return flag_extreme_values(df)


def value_pick():
    """P/E < 20, P/B < 3.0, D/E < 2.0, Dividend Yield > 1%"""
    df = load_universe()
    df = df[df["pe_ratio"] < 20]
    df = df[df["pb_ratio"] < 3.0]
    df = df[df["debt_to_equity"] < 2.0]
    df = df[df["dividend_yield_pct"] > 1]
    return flag_extreme_values(df)


def growth_accelerator():
    """PAT CAGR 5yr > 20%, Revenue CAGR 5yr > 15%, D/E < 2.0"""
    df = load_universe()
    df = df[df["pat_cagr_5yr"] > 20]
    df = df[df["revenue_cagr_5yr"] > 15]
    df = df[df["debt_to_equity"] < 2.0]
    return flag_extreme_values(df)


def dividend_champion():
    """Dividend Yield > 2%, Dividend Payout < 80%, FCF > 0"""
    df = load_universe()
    df = df[df["dividend_yield_pct"] > 2]
    df = df[df["dividend_payout_ratio_pct"] < 80]
    df = df[df["free_cash_flow_cr"] > 0]
    return flag_extreme_values(df)


def debt_free_blue_chip():
    """D/E = 0, ROE > 12%, Revenue > 5000 Crore"""
    df = load_universe()
    df = df[df["debt_to_equity"] == 0]
    df = df[df["return_on_equity_pct"] > 12]
    df = df[df["sales"] > 5000]
    return flag_extreme_values(df)


def turnaround_watch():
    """
    Revenue CAGR 3yr > 10%, FCF positive in latest year, D/E declining YoY.

    'D/E declining year-over-year' requires comparing TWO years per company(this year vs last year) 
    -- something the other 5 presets don't need, 
    since they only look at each company's single latest-year snapshot.
    This makes Turnaround Watch structurally different, handled separately below.
    """
    from sqlalchemy import create_engine
    db_engine = create_engine(f"sqlite:///{BASE_DIR / 'db' / 'nifty100.db'}")

    ratios = pd.read_sql("SELECT company_id, year, debt_to_equity FROM financial_ratios", db_engine)
    ratios_sorted = ratios.sort_values(["company_id", "year"])

    # Get each company's latest 2 years of D/E to check the YoY declining trend
    de_declining_companies = []
    for company_id, group in ratios_sorted.groupby("company_id"):
        if len(group) < 2:
            continue  # can't compare YoY with fewer than 2 years
        latest_two = group.tail(2)
        de_values = latest_two["debt_to_equity"].values
        if de_values[1] < de_values[0]:  # most recent D/E lower than prior year
            de_declining_companies.append(company_id)

    df = load_universe()
    df = df[df["company_id"].isin(de_declining_companies)]

    # Revenue CAGR 3yr requires a dedicated 3-year window computation --
    # flagging: current financial_ratios table only stores revenue_cagr_5yr (per Day 12's population), 
    # not a separate 3yr column. 
    # This preset's 3yr requirement cannot be fully applied until a revenue_cagr_3yr column is computed and added -- 
    # documenting as a known gap, not silently substituting the 5yr value in its place.
    df["turnaround_watch_note"] = "PARTIAL: revenue_cagr_3yr not yet in financial_ratios; only D/E-declining + FCF>0 applied"

    df = df[df["free_cash_flow_cr"] > 0]

    return flag_extreme_values(df)


PRESETS = {
    "Quality Compounder": quality_compounder,
    "Value Pick": value_pick,
    "Growth Accelerator": growth_accelerator,
    "Dividend Champion": dividend_champion,
    "Debt-Free Blue Chip": debt_free_blue_chip,
    "Turnaround Watch": turnaround_watch,
}


# Quick Smoke Test
def run_all_presets():
    """Runs all 6 presets, prints company counts, checks 5-50 range exit criteria."""
    print("=" * 60)
    print("RUNNING ALL 6 PRESET SCREENERS")
    print("=" * 60)

    results = {}
    for name, func in PRESETS.items():
        df = func()
        count = len(df)
        in_range = 5 <= count <= 50
        status = "[DONE]" if in_range else "[WARNING] OUT OF RANGE"
        print(f"{name}: {count} companies  {status}")
        results[name] = df

    return results


if __name__ == "__main__":
    results = run_all_presets()

    print("\n" + "=" * 60)
    print("QUALITY COMPOUNDER — sample results")
    print("=" * 60)
    print(results["Quality Compounder"][["company_id", "return_on_equity_pct", "debt_to_equity", "data_quality_flag"]].head(10))