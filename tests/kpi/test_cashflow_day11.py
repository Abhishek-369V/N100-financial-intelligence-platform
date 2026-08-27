"""
Day 11: Unit tests for FCF, CFO Quality, CapEx Intensity, FCF Conversion,
and the 8-pattern capital allocation classifier.
"""

import sys
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src" / "analytics"))

from cashflow_kpis import ( # type:ignore
    free_cash_flow, cfo_quality_score, capex_intensity,
    fcf_conversion_rate, classify_capital_allocation
)


def test_fcf_normal_case():
    assert free_cash_flow(operating_activity=500, investing_activity=-200) == 300

def test_fcf_negative_allowed():
    assert free_cash_flow(operating_activity=100, investing_activity=-300) == -200

def test_cfo_quality_high_quality():
    cfo = pd.Series([120, 130, 110, 140, 125])
    pat = pd.Series([100, 100, 100, 100, 100])
    score, label = cfo_quality_score(cfo, pat)
    assert label == "High Quality"

def test_cfo_quality_accrual_risk():
    cfo = pd.Series([30, 40, 35, 45, 30])
    pat = pd.Series([100, 100, 100, 100, 100])
    score, label = cfo_quality_score(cfo, pat)
    assert label == "Accrual Risk"

def test_cfo_quality_zero_pat_returns_none():
    cfo = pd.Series([50, 60])
    pat = pd.Series([0, 100])
    score, label = cfo_quality_score(cfo, pat)
    assert score is None
    assert label is None

def test_capex_intensity_asset_light():
    intensity, label = capex_intensity(investing_activity=-20, sales=1000)
    assert intensity == 2.0
    assert label == "Asset Light"

def test_capex_intensity_capital_intensive():
    intensity, label = capex_intensity(investing_activity=-150, sales=1000)
    assert intensity == 15.0
    assert label == "Capital Intensive"

def test_fcf_conversion_normal():
    assert fcf_conversion_rate(fcf=300, operating_profit=500) == 60.0

def test_fcf_conversion_zero_operating_profit():
    assert fcf_conversion_rate(fcf=100, operating_profit=0) is None

def test_classify_reinvestor_pattern():
    assert classify_capital_allocation(cfo=500, cfi=-200, cff=-100) == "Reinvestor"

def test_classify_distress_signal_pattern():
    assert classify_capital_allocation(cfo=-100, cfi=200, cff=150) == "Distress Signal"

def test_classify_shareholder_returns_with_high_cfo_pat():
    result = classify_capital_allocation(cfo=500, cfi=-200, cff=-100, cfo_pat_ratio=1.3)
    assert result == "Shareholder Returns"