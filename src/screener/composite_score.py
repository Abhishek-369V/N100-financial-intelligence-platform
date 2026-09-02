"""
Day 17: Composite quality score (0-100), winsorization, sector-relative normalization, and screener_output.xlsx generation.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from sqlalchemy import create_engine
import sys

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR / "src" / "analytics"))
sys.path.insert(0, str(BASE_DIR / "src" / "screener"))

from cagr import compute_cagr_for_window  #type:ignore
from presets import PRESETS, load_universe

OUTPUT_PATH = BASE_DIR / "output"
DB_PATH = BASE_DIR / "db" / "nifty100.db"
db_engine = create_engine(f"sqlite:///{DB_PATH}")


def winsorize(series, low_pct=10, high_pct=90):
    """
    Caps extreme values at the 10th and 90th percentile BEFORE scaling. 
    This is the formal fix for BEL/INDIGO-style outliers (4744% ROE, 892% ROE)
    -- instead of a company's absurd artifact value distorting the whole scoring range, 
    it gets pulled down to whatever the 90th percentile genuinely is across the real company universe.
    """
    if series.dropna().empty:
        return series
    lower = series.quantile(low_pct / 100)
    upper = series.quantile(high_pct / 100)
    return series.clip(lower=lower, upper=upper)


def scale_0_100(series, invert=False):
    """
    Min-max scales a (already winsorized) series to a 0-100 range.
    invert=True is used for metrics where LOWER is better (e.g., D/E) --
    flips the scale so a low D/E still produces a HIGH score.
    """
    if series.dropna().empty:
        return series
    min_val, max_val = series.min(), series.max()
    if max_val == min_val:
        return pd.Series([50] * len(series), index=series.index)  # no variance -> neutral midpoint
    scaled = (series - min_val) / (max_val - min_val) * 100
    return (100 - scaled) if invert else scaled


def compute_fcf_cagr_5yr(df):
    """
    FCF CAGR is required by the spec's scoring formula but was never computed in Sprint 2 
    -- cashflow_kpis.py built free_cash_flow() as a per-year value, not a growth-over-time metric. 
    Computing it here using the existing CAGR engine (Sprint 2's compute_cagr_for_window), 
    reusing proven logic rather than writing new formula code from scratch.
    """
    cf = pd.read_sql("SELECT company_id, year, operating_activity, investing_activity FROM cashflow", db_engine)
    cf["fcf"] = cf["operating_activity"] + cf["investing_activity"]

    fcf_cagr_results = {}
    for company_id in df["company_id"].unique():
        value, flag = compute_cagr_for_window(cf, company_id, "fcf", "year", 5)
        fcf_cagr_results[company_id] = value

    df = df.copy()
    df["fcf_cagr_5yr"] = df["company_id"].map(fcf_cagr_results)
    return df


def compute_composite_score(df, sector_relative=False):
    """
    Builds the 0-100 composite score per the spec's weighting:
    35% Profitability (ROE 15 + ROCE 10 + NPM 10)
    30% Cash Quality (FCF CAGR 15 + CFO/PAT 10 + FCF-positive flag 5)
    20% Growth (Revenue CAGR 10 + PAT CAGR 10)
    15% Leverage (D/E score 10 + ICR score 5)

    sector_relative=True normalizes each metric WITHIN each broad_sector
    (so a company is compared to its sector peers, not the whole universe)
    -- required separately by the spec as "sector-relative composite score."
    """
    df = df.copy()
    df = compute_fcf_cagr_5yr(df)

    def score_group(group):
        g = group.copy()

        # Profitability (35%)
        roe_scaled = scale_0_100(winsorize(g["return_on_equity_pct"]))
        roce_scaled = scale_0_100(winsorize(g["roce_percentage"])) if "roce_percentage" in g.columns else pd.Series(50, index=g.index)
        npm_scaled = scale_0_100(winsorize(g["net_profit_margin_pct"]))
        profitability = (roe_scaled * 0.15 + roce_scaled * 0.10 + npm_scaled * 0.10)

        # Cash Quality (30%)
        fcf_cagr_scaled = scale_0_100(winsorize(g["fcf_cagr_5yr"]))
        cfo_pat_scaled = scale_0_100(winsorize(g["cash_from_operations_cr"] / g["net_profit"].replace(0, np.nan)))
        fcf_positive_flag = (g["free_cash_flow_cr"] > 0).astype(int) * 100
        cash_quality = (fcf_cagr_scaled.fillna(0) * 0.15 + cfo_pat_scaled.fillna(0) * 0.10 + fcf_positive_flag * 0.05)

        # Growth (20%)
        rev_cagr_scaled = scale_0_100(winsorize(g["revenue_cagr_5yr"]))
        pat_cagr_scaled = scale_0_100(winsorize(g["pat_cagr_5yr"]))
        growth = (rev_cagr_scaled.fillna(0) * 0.10 + pat_cagr_scaled.fillna(0) * 0.10)

        # Leverage (15%) -- D/E inverted (lower is better), ICR normal (higher is better)
        de_scaled = scale_0_100(winsorize(g["debt_to_equity"]), invert=True)
        icr_for_scoring = g["interest_coverage"].fillna(1e9)  # Debt Free -> treated as max safety, same as Day 15's ICR rule
        icr_scaled = scale_0_100(winsorize(icr_for_scoring))
        leverage = (de_scaled * 0.10 + icr_scaled * 0.05)

        g["composite_quality_score"] = (profitability + cash_quality + growth + leverage).round(2)
        return g

    if sector_relative:
        return df.groupby("broad_sector", group_keys=False).apply(score_group)
    else:
        return score_group(df)


# Quick Smoke Test: let's verify the scoring output first -- before moving to the Excel generation half of Day 17!.. 
if __name__ == "__main__":
    universe = load_universe()
    scored = compute_composite_score(universe, sector_relative=False)
    sector_scored = compute_composite_score(universe, sector_relative=True)

    print("=" * 60)
    print("COMPOSITE SCORE — TOP 10 (GLOBAL)")
    print("=" * 60)
    print(scored.sort_values("composite_quality_score", ascending=False)
          [["company_id", "composite_quality_score", "return_on_equity_pct"]].head(10))

    print("\n" + "=" * 60)
    print("BEL / INDIGO CHECK — did winsorization neutralize the outliers?")
    print("=" * 60)
    for cid in ["BEL", "INDIGO"]:
        row = scored[scored["company_id"] == cid]
        if not row.empty:
            print(f"{cid}: raw ROE={row['return_on_equity_pct'].values[0]}%  "
                  f"composite_score={row['composite_quality_score'].values[0]}")