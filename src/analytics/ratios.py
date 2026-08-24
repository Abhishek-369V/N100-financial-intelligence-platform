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