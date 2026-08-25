"""  
SPRINT 2 
Day 8: Profitability ratios — NPM, OPM, ROE, ROCE, ROA
"""


def net_profit_margin(net_profit, sales):
    """
    NPM = net_profit / sales * 100 
    Measures: how much of every ₹1 of sales becomes actual profit.
    Returns None if sales = 0 ---> dividing by zero sales is meaningless, not "0%".
    """
    if sales == 0 or sales is None:
        return None
    return round((net_profit / sales) * 100, 2)


def operating_profit_margin(operating_profit, sales, reported_opm=None):
    """
    OPM = operating_profit / sales * 100
    Measures: profit from core operations only (before interest, tax, other income) —
    a cleaner view of the actual business, excluding one-off gains.

    Cross-checks our calculated OPM against the pre-existing 'opm_percentage'
    column already in the source data (Day 8 spec explicitly asks for this
    cross-check, logged if the two disagree by more than 1 percentage point —
    this catches data entry errors OR reveals our formula assumption is wrong).
    """
    if sales == 0 or sales is None:
        return None, False  # (value, mismatch_flag)

    calculated_opm = round((operating_profit / sales) * 100, 2)

    mismatch = False
    if reported_opm is not None:
        diff = abs(calculated_opm - reported_opm)
        if diff > 1:
            mismatch = True

    return calculated_opm, mismatch\


def return_on_equity(net_profit, equity_capital, reserves):
    """
    ROE = net_profit / (equity_capital + reserves) * 100
    Measures: how efficiently a company generates profit from shareholders' own money.
    'equity_capital + reserves' together = total shareholder equity on the balance sheet
    (equity_capital = face value of issued shares, reserves = accumulated retained profit).

    Returns None if equity+reserves <= 0 ---> a company with negative net worth
    (more liabilities than assets) makes ROE meaningless/misleading, not just "very high".
    """
    total_equity = equity_capital + reserves
    if total_equity <= 0:
        return None
    return round((net_profit / total_equity) * 100, 2)


def return_on_capital_employed(ebit, equity_capital, reserves, borrowings):
    """
    ROCE = EBIT / (equity + reserves + borrowings) * 100
    Measures: return generated on ALL capital used in the business — both
    shareholder money (equity) AND borrowed money (debt) — unlike ROE which
    only looks at shareholder money. This is why ROCE is considered a more
    complete efficiency measure than ROE alone.

    EBIT (Earnings Before Interest & Tax) approximated here as operating_profit
    + other_income, since that's what's available in our profitandloss table.

    For Financials sector (banks/NBFCs/insurance): per spec, we don't compare
    against an absolute threshold — high "capital employed" is structurally
    normal for a bank (their core business IS lending borrowed money), so a
    bank's ROCE isn't directly comparable to a manufacturing company's ROCE.
    This function just computes the number; the sector-relative comparison
    logic itself lives in Day 13's carve-out step, not here.
    """
    capital_employed = equity_capital + reserves + borrowings
    if capital_employed <= 0:
        return None
    roce = round((ebit / capital_employed) * 100, 2)
    return roce


def return_on_assets(net_profit, total_assets):
    """
    ROA = net_profit / total_assets * 100
    Measures: how efficiently a company uses everything it owns (assets) to
    generate profit — regardless of how those assets were funded (debt or equity).
    Returns None if total_assets = 0 (shouldn't happen with real data, but guards
    against a divide-by-zero crash if it does).
    """
    if total_assets == 0 or total_assets is None:
        return None
    return round((net_profit / total_assets) * 100, 2)


"""
Day 9 - Add Leverage & Efficiency Ratios:
"""

def debt_to_equity(borrowings, equity_capital, reserves):
    """
    D/E = borrowings / (equity_capital + reserves)
    Measures: how much a company relies on borrowed money vs its own capital.
    A D/E of 2 means the company has ₹2 of debt for every ₹1 of shareholder equity.

    Special case per spec: if borrowings = 0 (company has no debt at all),
    return 0 — NOT None. This is different from our Day 8 pattern (where zero
    denominator = undefined = None) because here borrowings=0 in the NUMERATOR
    is a perfectly valid, meaningful business state ("debt-free company"),
    not a broken calculation. None is reserved for when the ratio itself
    can't be computed (negative/zero equity denominator).
    """
    total_equity = equity_capital + reserves
    if total_equity <= 0:
        return None  # equity itself is invalid — ratio is undefined
    if borrowings == 0:
        return 0.0  # genuinely debt-free — a real, valid answer, not "missing data"
    return round(borrowings / total_equity, 4)


def high_leverage_flag(debt_to_equity_value, broad_sector):
    """
    Flags companies carrying unusually high debt relative to equity.
    Threshold: D/E > 5.
    Suppressed for Financials sector (banks/NBFCs) — high leverage is
    structurally normal for their business model (they lend borrowed money
    by design), so comparing them to a manufacturing company's D/E threshold
    would be misleading. This flag exists to catch risk in NON-financial
    companies specifically.
    """
    if debt_to_equity_value is None:
        return False
    if broad_sector == "Financials":
        return False
    return debt_to_equity_value > 5


def interest_coverage_ratio(operating_profit, other_income, interest):
    """
    ICR = (operating_profit + other_income) / interest
    Measures: how many times over a company can pay its interest expense
    from its operating earnings. An ICR of 3 means operating profit covers
    interest payments 3x over — a comfortable safety margin.

    Returns None if interest = 0. This isn't a broken calculation — it means
    the company has NO interest expense at all, i.e., it's debt-free (or has
    zero-interest debt). A ratio measuring "how well you cover interest" is
    meaningless for a company with nothing to cover — hence None, paired with
    a separate label (see icr_label below) that explains WHY it's None.
    """
    if interest == 0 or interest is None:
        return None
    return round((operating_profit + other_income) / interest, 2)


def icr_label(icr_value):
    """
    Companion label for ICR. When ICR is None (interest=0), we don't want
    the database or dashboard to just show a blank/null with no explanation —
    a human reading the table should immediately see WHY it's null.
    'Debt Free' is a much clearer signal than an unexplained empty cell.
    """
    if icr_value is None:
        return "Debt Free"
    return None  # no special label needed when ICR has a real numeric value


def icr_warning_flag(icr_value):
    """
    Flags companies at risk of NOT being able to cover their interest payments.
    Threshold: ICR < 1.5 — meaning operating profit barely covers (or fails
    to cover) interest expense, a classic early warning sign of financial distress.
    Only applies when ICR is a real number — a debt-free company (ICR=None)
    obviously isn't at risk of failing to cover interest it doesn't have.
    """
    if icr_value is None:
        return False
    return icr_value < 1.5


def net_debt(borrowings, investments):
    """
    Net Debt = borrowings - investments
    Measures: true debt burden after netting off liquid/investable assets
    the company could theoretically use to pay down debt if needed.
    'investments' is used here as a proxy for liquid assets (cash equivalents,
    marketable securities) per spec — a simplification, since we don't have
    a dedicated cash/cash-equivalents column, but investments is the closest
    available field representing liquid, realizable value.
    A negative Net Debt means the company holds MORE liquid assets than debt —
    effectively "net cash" — which is a genuinely strong position, not an error.
    """
    return round(borrowings - investments, 2)


def asset_turnover(sales, total_assets):
    """
    Asset Turnover = sales / total_assets
    Measures: how efficiently a company generates sales from its total asset base.
    A ratio of 1.5 means every ₹1 of assets generates ₹1.50 of sales — higher
    is generally more efficient (though "good" varies heavily by industry —
    a retailer naturally turns over assets faster than a utility company).
    Returns None if total_assets = 0 — a real edge case guard, not expected
    to occur with valid data, but present to prevent a pipeline crash if it does.
    """
    if total_assets == 0 or total_assets is None:
        return None
    return round(sales / total_assets, 4)