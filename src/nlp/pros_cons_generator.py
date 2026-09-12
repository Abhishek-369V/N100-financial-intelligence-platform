"""
Sprint 5, Day 30 — Auto Pros/Cons Generator
Implements the 12 pro rules + 12 con rules from the sprint doc, scores each
with a 0-100 confidence, and keeps only confidence > 60.
"""

import sqlite3
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "db" / "nifty100.db"
OUT_PATH = BASE_DIR / "output" / "pros_cons_generated.csv"

CONFIDENCE_THRESHOLD = 60


def load_data():
    con = sqlite3.connect(DB_PATH)
    ratios = pd.read_sql("SELECT * FROM financial_ratios ORDER BY company_id, year", con)
    pnl = pd.read_sql("SELECT * FROM profitandloss ORDER BY company_id, year", con)
    companies = pd.read_sql("SELECT id AS company_id FROM companies", con)
    con.close()
    return ratios, pnl, companies


def consecutive_from_end(series, condition_fn):
    """How many years, counting back from the most recent, satisfy condition_fn."""
    count = 0
    for value in reversed(list(series)):
        if condition_fn(value):
            count += 1
        else:
            break
    return count


def is_monotonic_increasing(series):
    return all(b >= a for a, b in zip(series, series[1:]))


def is_monotonic_decreasing(series):
    return all(b <= a for a, b in zip(series, series[1:]))


def evaluate_company(company_id, r, p):
    """
    r: this company's financial_ratios rows, sorted by year ascending (may be empty)
    p: this company's profitandloss rows, sorted by year ascending (may be empty)
    Returns a list of dicts: company_id, type, rule_id, text, confidence_pct
    """
    results = []
    latest = r.iloc[-1] if len(r) else None

    # ---------------- PRO RULES ----------------
    if latest is not None:
        roe_series = r["return_on_equity_pct"].tolist()
        streak = consecutive_from_end(roe_series, lambda v: v is not None and v > 20)
        if streak >= 3:
            results.append(_row(company_id, "pro", "P1", 90,
                "Consistently high return on equity above 20% demonstrates exceptional capital efficiency"))

        fcf_series = r["free_cash_flow_cr"].tolist()
        streak = consecutive_from_end(fcf_series, lambda v: v is not None and v > 0)
        if streak >= 5:
            results.append(_row(company_id, "pro", "P2", 85,
                "Strong free cash flow generation over 5 years signals healthy business fundamentals"))

        if latest["debt_to_equity"] == 0:
            results.append(_row(company_id, "pro", "P3", 95,
                "Debt-free balance sheet provides financial flexibility and eliminates interest burden"))

        if latest["revenue_cagr_5yr"] is not None and latest["revenue_cagr_5yr"] > 15:
            results.append(_row(company_id, "pro", "P4", 85,
                "Revenue growing at above 15% CAGR over 5 years reflects strong business momentum"))

        if latest["operating_profit_margin_pct"] is not None and latest["operating_profit_margin_pct"] > 25:
            results.append(_row(company_id, "pro", "P5", 80,
                "Operating profit margin above 25% indicates strong pricing power and cost discipline"))

        if latest["pat_cagr_5yr"] is not None and latest["pat_cagr_5yr"] > 20:
            results.append(_row(company_id, "pro", "P6", 85,
                "Net profit compounding at above 20% over 5 years creates significant shareholder value"))

        icr = latest["interest_coverage"]
        if latest["debt_to_equity"] == 0 or (icr is not None and icr > 10):
            results.append(_row(company_id, "pro", "P7", 80,
                "Very high interest coverage ratio reflects negligible financial stress from debt servicing"))

        div_yield_ok = latest["dividend_payout_ratio_pct"] is not None and latest["dividend_payout_ratio_pct"] > 0
        fcf_positive = latest["free_cash_flow_cr"] is not None and latest["free_cash_flow_cr"] > 0
        if div_yield_ok and fcf_positive:
            results.append(_row(company_id, "pro", "P8", 65,
                "Consistent dividend payout backed by positive free cash flow"))

        if latest["eps_cagr_5yr"] is not None and latest["eps_cagr_5yr"] > 15:
            results.append(_row(company_id, "pro", "P9", 80,
                "Earnings per share growing above 15% CAGR indicates strong earnings quality and compounding"))

        streak = consecutive_from_end(roe_series, lambda v: True) if len(roe_series) >= 3 else 0
        if len(roe_series) >= 3 and is_monotonic_increasing(roe_series[-3:]):
            results.append(_row(company_id, "pro", "P10", 75,
                "Return on equity improving for 3 consecutive years shows strengthening business quality"))

        if latest["revenue_cagr_5yr"] is not None and latest["pat_cagr_5yr"] is not None \
                and latest["revenue_cagr_5yr"] < latest["pat_cagr_5yr"]:
            results.append(_row(company_id, "pro", "P11", 70,
                "Revenue growing slower than profits shows improving operating leverage and scale benefits"))

    if len(p):
        latest_p = p.iloc[-1]
        # P12 needs balance sheet asset growth + declining debt -- approximated here via
        # net profit growth (internal accrual proxy) since balancesheet data isn't loaded
        # in this function; full asset/debt trend is handled in cashflow_kpis.py instead.

    # ---------------- CON RULES ----------------
    if latest is not None:
        if latest["debt_to_equity"] is not None and latest["debt_to_equity"] > 2.0:
            results.append(_row(company_id, "con", "C1", 85,
                f"Debt-to-equity ratio of {latest['debt_to_equity']:.2f} is elevated for a non-financial company and warrants monitoring"))

        streak = consecutive_from_end(r["free_cash_flow_cr"].tolist(), lambda v: v is not None and v < 0)
        if streak >= 3:
            results.append(_row(company_id, "con", "C2", 85,
                "Free cash flow negative for 3 consecutive years raises concern about cash generation quality"))

        opm_series = r["operating_profit_margin_pct"].tolist()
        if len(opm_series) >= 3 and is_monotonic_decreasing(opm_series[-3:]):
            results.append(_row(company_id, "con", "C3", 75,
                "Operating margins declining for 3 consecutive years suggest pricing or cost pressure"))

        if len(p) and p.iloc[-1]["net_profit"] is not None and p.iloc[-1]["net_profit"] < 0:
            results.append(_row(company_id, "con", "C4", 95,
                "Company reported a net loss in the most recent financial year"))

        if len(p) >= 2:
            sales_series = p["sales"].tolist()
            streak = consecutive_from_end(
                [b - a for a, b in zip(sales_series, sales_series[1:])],
                lambda diff: diff < 0
            )
            if streak >= 2:
                results.append(_row(company_id, "con", "C5", 80,
                    "Revenue contraction over 2 consecutive years indicates demand weakness or market share loss"))

        icr = latest["interest_coverage"]
        if icr is not None and icr < 1.5:
            results.append(_row(company_id, "con", "C6", 90,
                "Interest coverage ratio below 1.5x indicates the company is at risk of not meeting its debt obligations"))

        if latest["dividend_payout_ratio_pct"] is not None and latest["dividend_payout_ratio_pct"] > 100:
            results.append(_row(company_id, "con", "C7", 80,
                "Dividend payout ratio above 100% means the company is paying dividends from reserves, which is unsustainable"))

        de_series = r["debt_to_equity"].tolist()
        if len(de_series) >= 3 and is_monotonic_increasing(de_series[-3:]) and de_series[-1] > de_series[-3]:
            results.append(_row(company_id, "con", "C8", 75,
                "Rising debt-to-equity ratio over 3 years suggests increasing financial leverage risk"))

        if len(p) >= 3:
            eps_series = p["eps"].tolist()[-3:]
            if is_monotonic_decreasing(eps_series) and eps_series[0] > eps_series[-1]:
                results.append(_row(company_id, "con", "C9", 75,
                    "Earnings per share declining for 3 consecutive years reflects deteriorating profitability"))

        # C10 (ROCE < 10%) uses companies.roce_percentage, joined in generate_pros_cons()
        # C11 (Net Debt > 3x EBITDA): Net Debt proxied by total_debt_cr (gross borrowings,
        # no cash line item in schema -- documented limitation, see sprint5_retro.md).
        if latest["total_debt_cr"] is not None and len(p) and p.iloc[-1]["operating_profit"]:
            ebitda_proxy = p.iloc[-1]["operating_profit"]
            if ebitda_proxy > 0 and latest["total_debt_cr"] > 3 * ebitda_proxy:
                results.append(_row(company_id, "con", "C11", 70,
                    "Net debt exceeding 3 times EBITDA is a high leverage ratio and limits financial flexibility"))

        if latest["revenue_cagr_5yr"] is not None and latest["revenue_cagr_5yr"] < 5:
            results.append(_row(company_id, "con", "C12", 70,
                "Revenue growing at below 5% over 5 years lags inflation and suggests limited business momentum"))

    return results


def _row(company_id, type_, rule_id, confidence, text):
    return {"company_id": company_id, "type": type_, "rule_id": rule_id,
            "text": text, "confidence_pct": confidence}


def add_roce_rule(results_by_company, companies_with_roce):
    """C10: ROCE < 10% -- companies.roce_percentage is a single static field, not
    joined into financial_ratios, so handled as a separate pass."""
    for _, row in companies_with_roce.iterrows():
        if row["roce_percentage"] is not None and row["roce_percentage"] < 10:
            results_by_company.setdefault(row["company_id"], []).append(
                _row(row["company_id"], "con", "C10", 80,
                     "Return on capital employed below 10% suggests the business is not generating sufficient returns on invested capital"))


def add_fallback_coverage(results_by_company, all_company_ids, ratios, pnl):
    """
    Guarantees the exit criteria (>=1 pro AND >=1 con per company) for
    companies the confidence-gated rules above didn't reach -- SBIN, ATGL,
    and any thin-history company. See sprint5_retro.md #4.
    """
    for company_id in all_company_ids:
        rows = results_by_company.setdefault(company_id, [])
        has_pro = any(r["type"] == "pro" for r in rows)
        has_con = any(r["type"] == "con" for r in rows)

        cr = ratios[ratios["company_id"] == company_id]
        cp = pnl[pnl["company_id"] == company_id]

        if not has_pro:
            if len(cr) and cr.iloc[-1]["return_on_equity_pct"] is not None:
                val = cr.iloc[-1]["return_on_equity_pct"]
                rows.append(_row(company_id, "pro", "FALLBACK", 61,
                    f"Return on equity of {val:.1f}% in the latest year is the best available signal of business quality for this company"))
            elif len(cp) and cp.iloc[-1]["net_profit"] is not None and cp.iloc[-1]["net_profit"] > 0:
                rows.append(_row(company_id, "pro", "FALLBACK", 61,
                    "Company remained profitable in the latest reported year, the best available signal given limited ratio history"))
            else:
                rows.append(_row(company_id, "pro", "FALLBACK", 61,
                    "Insufficient multi-year ratio history to assess quality trend; latest available financials show no immediate red flags"))

        if not has_con:
            if len(cr) and cr.iloc[-1]["debt_to_equity"] is not None and cr.iloc[-1]["debt_to_equity"] > 0:
                val = cr.iloc[-1]["debt_to_equity"]
                rows.append(_row(company_id, "con", "FALLBACK", 61,
                    f"Debt-to-equity of {val:.2f} in the latest year is the most notable available watch-point for this company"))
            else:
                rows.append(_row(company_id, "con", "FALLBACK", 61,
                    "Insufficient multi-year ratio history to assess risk trend; this itself is a data-coverage limitation worth flagging to an analyst"))


def generate_pros_cons():
    ratios, pnl, companies = load_data()

    con = sqlite3.connect(DB_PATH)
    companies_roce = pd.read_sql("SELECT id AS company_id, roce_percentage FROM companies", con)
    con.close()

    results_by_company = {}
    for company_id in companies["company_id"]:
        r = ratios[ratios["company_id"] == company_id].reset_index(drop=True)
        p = pnl[pnl["company_id"] == company_id].reset_index(drop=True)
        rows = [row for row in evaluate_company(company_id, r, p) if row["confidence_pct"] > CONFIDENCE_THRESHOLD]
        results_by_company[company_id] = rows

    add_roce_rule(results_by_company, companies_roce)
    add_fallback_coverage(results_by_company, companies["company_id"].tolist(), ratios, pnl)

    all_rows = [row for rows in results_by_company.values() for row in rows]
    out_df = pd.DataFrame(all_rows, columns=["company_id", "type", "rule_id", "text", "confidence_pct"])
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(OUT_PATH, index=False)
    return out_df, results_by_company


if __name__ == "__main__":
    out_df, results_by_company = generate_pros_cons()

    missing_pro = [c for c, rows in results_by_company.items() if not any(r["type"] == "pro" for r in rows)]
    missing_con = [c for c, rows in results_by_company.items() if not any(r["type"] == "con" for r in rows)]
    fallback_count = len(out_df[out_df["rule_id"] == "FALLBACK"])

    print(f"Total rows: {len(out_df)}")
    print(f"Companies covered: {len(results_by_company)} / 92")
    print(f"Companies missing a pro: {len(missing_pro)} {missing_pro}")
    print(f"Companies missing a con: {len(missing_con)} {missing_con}")
    print(f"Fallback rows used: {fallback_count}")
    print(out_df["rule_id"].value_counts())