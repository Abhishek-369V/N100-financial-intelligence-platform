"""
Day 11: Free Cash Flow, CFO Quality Score, CapEx Intensity, FCF Conversion Rate,
        and the 8-pattern capital allocation classifier.

What this measures: 
- Day 8-10 answered: "is the company profitable and growing?" 
- Day 11 answers a different question: "is the reported profit actually turning into real cash, or just accounting paper?"

"""

import pandas as pd


def free_cash_flow(operating_activity, investing_activity):
    """
    FCF = operating_activity + investing_activity
    Measures: cash actually left over after running the business AND after
    capital spending (buying equipment, etc.) — the real cash a company could
    use for debt repayment, dividends, or buybacks.
    Negative FCF is explicitly allowed (per spec) — a growing company investing
    heavily can have negative FCF and still be healthy; it's not an error state.
    """
    return round(operating_activity + investing_activity, 2)


def cfo_quality_score(cfo_series, pat_series):
    """
    CFO Quality Score = average(CFO / PAT) over up to 5 years.
    Measures: does reported profit (PAT) actually show up as real cash (CFO)?
    A ratio near 1.0 means "yes, profit = cash". A ratio well below 1.0 means
    profit exists mostly on paper (e.g., unpaid receivables) — a real red flag
    called 'accrual risk' in accounting.

    cfo_series, pat_series: pandas Series of up to 5 years of values, same length,
    aligned by year (caller's responsibility to pass matching years).

    Returns (score, label). Returns (None, None) if PAT is 0 anywhere,
    since dividing by zero profit is undefined -- not a valid ratio.
    """
    if (pat_series == 0).any():
        return None, None

    ratios = cfo_series / pat_series
    avg_ratio = ratios.mean()

    if avg_ratio > 1.0:
        label = "High Quality"
    elif avg_ratio >= 0.5:
        label = "Moderate"
    else:
        label = "Accrual Risk"

    return round(avg_ratio, 2), label


def capex_intensity(investing_activity, sales):
    """
    CapEx Intensity = abs(investing_activity) / sales * 100
    Measures: how much of every ₹1 of sales gets reinvested into capital
    expenditure (factories, equipment). abs() is used because investing_activity
    is typically negative (cash going OUT to buy assets) — we care about the
    magnitude of spending relative to sales, not its sign here.
    """
    if sales == 0 or sales is None:
        return None, None

    intensity = round((abs(investing_activity) / sales) * 100, 2)

    if intensity < 3:
        label = "Asset Light"
    elif intensity <= 8:
        label = "Moderate"
    else:
        label = "Capital Intensive"

    return intensity, label


def fcf_conversion_rate(fcf, operating_profit):
    """
    FCF Conversion Rate = FCF / operating_profit * 100
    Measures: what percentage of operating profit actually converts into free
    cash flow. High conversion = efficient, cash-generative business.
    Returns None if operating_profit = 0 -- can't meaningfully express a
    conversion rate against zero operating profit.
    """
    if operating_profit == 0 or operating_profit is None:
        return None
    return round((fcf / operating_profit) * 100, 2)


def classify_capital_allocation(cfo, cfi, cff, cfo_pat_ratio=None):
    """
    Classifies a company-year into one of 8 capital allocation patterns based
    on the SIGN (positive/negative) of three cash flow types:
      CFO = Cash from Operating activities
      CFI = Cash from Investing activities
      CFF = Cash from Financing activities

    The intuition behind each pattern:
    - (+,-,-) Reinvestor: making cash from operations, spending it on growth
      (investing), paying down debt/returning capital (financing) -- healthy,
      self-funded growth.
    - (+,-,-) with high CFO/PAT specifically -> relabeled 'Shareholder Returns'
      if the company is ALSO converting profit to cash efficiently (uses the
      optional cfo_pat_ratio input to distinguish this from plain Reinvestor).
    - (+,+,-) Liquidating Assets: making operating cash AND selling off assets
      (positive investing = asset sales) while paying down financing -- could
      signal shrinking the business.
    - (-,+,+) Distress Signal: losing cash from operations, selling assets,
      AND taking on new financing just to stay afloat -- a warning pattern.
    - (-,-,+) Growth Funded by Debt: losing operating cash, still spending on
      investment, funding it all with new debt/equity raises -- risky if
      operations don't turn around.
    - (+,+,+) Cash Accumulator: cash coming in from all three sources --
      unusual, often a one-off event (large asset sale + fundraise + profit).
    - (-,-,-) Pre-Revenue: burning cash everywhere -- typical of early-stage
      or deeply distressed companies.
    - (+,-,+) Mixed: profitable and raising capital while investing -- often
      an expansion-phase company.

    Returns a string label.
    """
    cfo_sign = "+" if cfo > 0 else "-"
    cfi_sign = "+" if cfi > 0 else "-"
    cff_sign = "+" if cff > 0 else "-"

    pattern = (cfo_sign, cfi_sign, cff_sign)

    if pattern == ("+", "-", "-"):
        if cfo_pat_ratio is not None and cfo_pat_ratio > 1.0:
            return "Shareholder Returns"
        return "Reinvestor"
    elif pattern == ("+", "+", "-"):
        return "Liquidating Assets"
    elif pattern == ("-", "+", "+"):
        return "Distress Signal"
    elif pattern == ("-", "-", "+"):
        return "Growth Funded by Debt"
    elif pattern == ("+", "+", "+"):
        return "Cash Accumulator"
    elif pattern == ("-", "-", "-"):
        return "Pre-Revenue"
    elif pattern == ("+", "-", "+"):
        return "Mixed"
    else:
        # (-,+,-) is the one sign combination not named in the spec's 8 patterns
        return "Unclassified"


def generate_capital_allocation_output(df):
    """
    Runs classify_capital_allocation() across every company-year row in df,
    returns a DataFrame ready to save as output/capital_allocation.csv.
    df must have columns: company_id, year, operating_activity,
    investing_activity, financing_activity.
    """
    results = []
    for _, row in df.iterrows():
        label = classify_capital_allocation(
            cfo=row["operating_activity"],
            cfi=row["investing_activity"],
            cff=row["financing_activity"],
        )
        results.append({
            "company_id": row["company_id"],
            "year": row["year"],
            "cfo_sign": "+" if row["operating_activity"] > 0 else "-",
            "cfi_sign": "+" if row["investing_activity"] > 0 else "-",
            "cff_sign": "+" if row["financing_activity"] > 0 else "-",
            "pattern_label": label,
        })
    return pd.DataFrame(results)