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


def detect_distress_signal(cfo, cff):
    """
    Distress Signal: CFO < 0 AND CFF > 0 in the latest year -- raising cash
    from financing (new debt/equity) while operations are burning cash.
    A classic "propping up the business with outside money" red flag.
    """
    return cfo < 0 and cff > 0


def detect_deleveraging(cff, borrowings_current, borrowings_prior):
    """
    Deleveraging: CFF < 0 AND borrowings declining year-over-year --
    actively paying down debt rather than just having a negative financing
    year for some other reason (e.g. a big dividend payout with flat debt).
    Returns False (not None) when prior-year borrowings are unavailable,
    since "can't confirm a decline" is not the same claim as "found a decline".
    """
    if borrowings_prior is None or borrowings_current is None:
        return False
    return cff < 0 and borrowings_current < borrowings_prior


def fcf_cagr(fcf_series):
    """
    CAGR of free cash flow across up to 5 years: (end/start)^(1/n) - 1, in %.
    GAP: CAGR is mathematically undefined when the start or end value is
    <= 0 (can't take a root of a negative/zero base) -- FCF is explicitly
    allowed to be negative (see free_cash_flow() docstring), so this is a
    real, expected case here, not an edge case to crash on. Returns None
    in that situation rather than a fabricated/misleading number, and the
    caller (generate_cashflow_intelligence_output) surfaces that as a
    genuine "N/A", not a silent zero.
    """
    series = list(fcf_series)
    if len(series) < 2:
        return None
    start, end = series[0], series[-1]
    n = len(series) - 1
    if start <= 0 or end <= 0:
        return None
    return round(((end / start) ** (1 / n) - 1) * 100, 2)


def generate_cashflow_intelligence_output(cashflow_df, pnl_df, bs_df, sectors_df, companies_ids):
    """
    Builds one row per company for output/cashflow_intelligence.xlsx with:
    company_id, sector, cfo_quality_score, cfo_quality_label,
    capex_intensity_pct, capex_label, fcf_cagr_5yr, fcf_conversion_pct,
    distress_flag, deleveraging_flag, capital_allocation_label

    All four input DataFrames are expected sorted by year ascending per
    company (caller's responsibility, same convention as the rest of this
    module) so "latest" = .iloc[-1] and "last N years" = .tail(N).
    """
    rows = []
    for company_id in companies_ids:
        cf = cashflow_df[cashflow_df["company_id"] == company_id].reset_index(drop=True)
        p = pnl_df[pnl_df["company_id"] == company_id].reset_index(drop=True)
        bs = bs_df[bs_df["company_id"] == company_id].reset_index(drop=True)
        sector_match = sectors_df[sectors_df["company_id"] == company_id]
        sector = sector_match.iloc[0]["broad_sector"] if len(sector_match) else None

        if len(cf) == 0:
            # No cash flow history at all for this company -- can't compute any
            # of these features. Emit a row of Nones rather than skipping the
            # company outright, so it still appears in the 92-row output file
            # (Sprint 6 Gate AC-15-style expectation of full coverage).
            rows.append({
                "company_id": company_id, "sector": sector,
                "cfo_quality_score": None, "cfo_quality_label": None,
                "capex_intensity_pct": None, "capex_label": None,
                "fcf_cagr_5yr": None, "fcf_conversion_pct": None,
                "distress_flag": None, "deleveraging_flag": None,
                "capital_allocation_label": None,
            })
            continue

        cf_5yr = cf.tail(5)
        merged_5yr = cf_5yr.merge(p[["year", "net_profit"]], on="year", how="left")

        if merged_5yr["net_profit"].notna().all() and len(merged_5yr) > 0:
            quality_score, quality_label = cfo_quality_score(
                merged_5yr["operating_activity"], merged_5yr["net_profit"]
            )
        else:
            quality_score, quality_label = None, None

        latest_cf = cf.iloc[-1]
        latest_p_match = p[p["year"] == latest_cf["year"]]
        latest_sales = latest_p_match.iloc[0]["sales"] if len(latest_p_match) else None
        latest_op_profit = latest_p_match.iloc[0]["operating_profit"] if len(latest_p_match) else None

        capex_pct, capex_label = capex_intensity(latest_cf["investing_activity"], latest_sales)

        fcf_series = cf_5yr["operating_activity"] + cf_5yr["investing_activity"]
        cagr = fcf_cagr(fcf_series)

        latest_fcf = free_cash_flow(latest_cf["operating_activity"], latest_cf["investing_activity"])
        conversion = fcf_conversion_rate(latest_fcf, latest_op_profit)

        distress = detect_distress_signal(latest_cf["operating_activity"], latest_cf["financing_activity"])

        borrowings_current = borrowings_prior = None
        if len(bs) >= 2:
            latest_bs = bs[bs["year"] == latest_cf["year"]]
            prior_year_rows = bs[bs["year"] < latest_cf["year"]]
            if len(latest_bs):
                borrowings_current = latest_bs.iloc[0]["borrowings"]
            if len(prior_year_rows):
                borrowings_prior = prior_year_rows.iloc[-1]["borrowings"]
        deleveraging = detect_deleveraging(latest_cf["financing_activity"], borrowings_current, borrowings_prior)

        cfo_pat_ratio = None
        if latest_p_match.iloc[0]["net_profit"] if len(latest_p_match) else 0:
            net_profit = latest_p_match.iloc[0]["net_profit"]
            if net_profit != 0:
                cfo_pat_ratio = latest_cf["operating_activity"] / net_profit
        pattern_label = classify_capital_allocation(
            latest_cf["operating_activity"], latest_cf["investing_activity"],
            latest_cf["financing_activity"], cfo_pat_ratio=cfo_pat_ratio,
        )

        rows.append({
            "company_id": company_id, "sector": sector,
            "cfo_quality_score": quality_score, "cfo_quality_label": quality_label,
            "capex_intensity_pct": capex_pct, "capex_label": capex_label,
            "fcf_cagr_5yr": cagr, "fcf_conversion_pct": conversion,
            "distress_flag": distress, "deleveraging_flag": deleveraging,
            "capital_allocation_label": pattern_label,
        })

    return pd.DataFrame(rows)


def generate_distress_alerts(cashflow_intelligence_df, cashflow_df, pnl_df):
    """
    output/distress_alerts.csv -- companies flagged with distress signal,
    including CFO value, CFF value, and latest net profit (per spec).

    CAVEAT (not filtered out, just labelled): CFO<0 AND CFF>0 is the given
    spec definition, but for Financials-sector companies (banks, NBFCs)
    this pattern is close to their normal business model -- loan
    disbursements count as operating outflow, and raising deposits/
    borrowings is routine financing, not distress. 9 of the 13 flagged
    companies here are Financials with strong positive net profit (e.g.
    AXISBANK: CFO -5,555cr, net profit +24,861cr) -- clearly not actual
    distress. Added a sector column so a reader isn't misled into reading
    every row here as equally alarming; a real analyst pass would filter
    non-financials for the genuine warning signals.
    """
    flagged = cashflow_intelligence_df[cashflow_intelligence_df["distress_flag"] == True]
    rows = []
    for _, row in flagged.iterrows():
        company_id = row["company_id"]
        cf = cashflow_df[cashflow_df["company_id"] == company_id].sort_values("year")
        p = pnl_df[pnl_df["company_id"] == company_id].sort_values("year")
        if len(cf) == 0:
            continue
        latest_cf = cf.iloc[-1]
        latest_p_match = p[p["year"] == latest_cf["year"]]
        net_profit = latest_p_match.iloc[0]["net_profit"] if len(latest_p_match) else None
        rows.append({
            "company_id": company_id,
            "sector": row["sector"],
            "cfo_value": latest_cf["operating_activity"],
            "cff_value": latest_cf["financing_activity"],
            "latest_net_profit": net_profit,
            "likely_financial_sector_pattern": row["sector"] == "Financials",
        })
    return pd.DataFrame(rows)


def generate_capital_allocation_output(df):
    """
    Runs classify_capital_allocation() across every company-year row in df,
    returns a DataFrame ready to save as output/capital_allocation.csv.
    df must have columns: company_id, year, operating_activity,
    investing_activity, financing_activity, and (for the Shareholder Returns
    split) net_profit -- CFO/PAT is computed inline per row here.

    BUGFIX (carried over from Sprint 4 retro): this used to call
    classify_capital_allocation() without cfo_pat_ratio at all, so
    "Shareholder Returns" could never be produced -- every (+,-,-) row
    fell back to "Reinvestor" regardless of cash quality. Now computes
    CFO/PAT per row (when net_profit is available and non-zero) and
    passes it through, matching the function's own documented intent.
    """
    results = []
    for _, row in df.iterrows():
        cfo_pat_ratio = None
        if "net_profit" in df.columns:
            net_profit = row["net_profit"]
            if pd.notna(net_profit) and net_profit != 0:
                cfo_pat_ratio = row["operating_activity"] / net_profit

        label = classify_capital_allocation(
            cfo=row["operating_activity"],
            cfi=row["investing_activity"],
            cff=row["financing_activity"],
            cfo_pat_ratio=cfo_pat_ratio,
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


if __name__ == "__main__":
    import sqlite3
    from pathlib import Path

    base_dir = Path(__file__).resolve().parent.parent.parent
    con = sqlite3.connect(base_dir / "db" / "nifty100.db")
    cashflow_df = pd.read_sql("SELECT * FROM cashflow ORDER BY company_id, year", con)
    pnl_df = pd.read_sql("SELECT * FROM profitandloss ORDER BY company_id, year", con)
    bs_df = pd.read_sql("SELECT * FROM balancesheet ORDER BY company_id, year", con)
    sectors_df = pd.read_sql("SELECT company_id, broad_sector FROM sectors", con)
    companies_ids = pd.read_sql("SELECT id AS company_id FROM companies", con)["company_id"].tolist()
    con.close()

    out_dir = base_dir / "output"
    out_dir.mkdir(parents=True, exist_ok=True)

    ci_df = generate_cashflow_intelligence_output(cashflow_df, pnl_df, bs_df, sectors_df, companies_ids)
    ci_df.to_excel(out_dir / "cashflow_intelligence.xlsx", index=False)

    alerts_df = generate_distress_alerts(ci_df, cashflow_df, pnl_df)
    alerts_df.to_csv(out_dir / "distress_alerts.csv", index=False)

    print(f"cashflow_intelligence.xlsx rows: {len(ci_df)} / 92")
    print(f"Rows with no cash flow history: {(ci_df['cfo_quality_label'].isna()).sum()}")
    print(f"Distress alerts: {len(alerts_df)}")
    print(ci_df["capital_allocation_label"].value_counts())
    print(ci_df["cfo_quality_label"].value_counts(dropna=False))
    print(ci_df["capex_label"].value_counts(dropna=False))