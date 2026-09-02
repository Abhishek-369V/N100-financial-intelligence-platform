"""
Day 17: Verification tests for winsorization and composite scoring.
"""
import pandas as pd
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src" / "screener"))

from composite_score import winsorize, scale_0_100, compute_composite_score #type:ignore
from presets import load_universe #type:ignore


def test_winsorize_caps_extreme_high_value():
    series = pd.Series([10, 20, 30, 40, 5000])  # 5000 is an obvious outlier
    result = winsorize(series, low_pct=10, high_pct=90)
    assert result.max() < 5000  # the outlier must be pulled down
    assert result.max() == series.quantile(0.90)


def test_scale_0_100_normal_case():
    series = pd.Series([0, 50, 100])
    scaled = scale_0_100(series)
    assert scaled.min() == 0
    assert scaled.max() == 100


def test_scale_0_100_invert_flips_direction():
    series = pd.Series([1, 2, 3])  # lower should score HIGHER when inverted (e.g., D/E)
    scaled = scale_0_100(series, invert=True)
    assert scaled.iloc[0] > scaled.iloc[2]  # value=1 (lowest) should score highest


def test_bel_extreme_roe_does_not_dominate_composite_score():
    """
    Regression test: confirms the specific bug we found and fixed — a company with an absurd raw ROE (BEL, HAL-style artifact) 
    should NOT produce a composite score that implausibly outranks genuinely strong companies, after winsorization is applied.
    """
    universe = load_universe()
    scored = compute_composite_score(universe, sector_relative=False)

    bel_row = scored[scored["company_id"] == "BEL"]
    if not bel_row.empty:
        # BEL's raw ROE is ~4744% -- composite score must be well under 100,
        # proving winsorization capped its contribution rather than letting
        # the extreme value inflate the score toward the maximum.
        assert bel_row["composite_quality_score"].values[0] < 90


def test_indigo_winsorized_roe_matches_90th_percentile():
    """
    Confirms winsorize() genuinely caps at the true 90th percentile of the REAL dataset, 
    not an arbitrary fixed number -- this is what we verified manually and are now locking in as an automated regression check.
    """
    universe = load_universe()
    roe_90th = universe["return_on_equity_pct"].quantile(0.90)
    winsorized = winsorize(universe["return_on_equity_pct"])
    indigo_value = winsorized[universe["company_id"] == "INDIGO"].values[0]
    assert abs(indigo_value - roe_90th) < 0.01