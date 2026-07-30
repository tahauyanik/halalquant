"""
screening_logic.py

Pure financial-ratio screening logic for HalalQuant, kept separate from
the Streamlit UI (app.py) so it can be unit-tested without spinning up
a web server. See test_filters.py for the accompanying test suite.

Methodology note: these four ratios (debt, interest income, cash,
receivables — each measured against average market cap) follow the
style of ratio-based screens used by providers such as Dow Jones
Islamic Market and S&P Shariah. They are NOT identical to AAOIFI's
own Shari'ah Standard No. 21 (which uses a 30% threshold, three
ratios, and no receivables ratio), and they do NOT reflect the
official BIST Katilim Endeksi determination, which is based on
company-submitted KAFIF forms reviewed by the TKBB Advisory Board
plus qualitative business-activity screening. See the in-app
disclaimer for details.
"""

import pandas as pd

DEBT_THRESHOLD = 33
INTEREST_THRESHOLD = 5
CASH_THRESHOLD = 33
RECEIVABLES_THRESHOLD = 33

CASH_ROW_NAMES = [
    "Cash And Cash Equivalents",
    "Cash Cash Equivalents And Short Term Investments",
]
RECEIVABLES_ROW_NAMES = [
    "Receivables",
    "Accounts Receivable",
    "Gross Accounts Receivable",
]
REVENUE_ROW_NAMES = ["Total Revenue", "Operating Revenue"]
INTEREST_INCOME_ROW_NAMES = [
    "Interest Income",
    "Non Operating Interest Income",
    "Interest Income Non Operating",
]


def _get_latest_value(series_or_scalar):
    """
    Extract the most recent single value from a pandas Series/row
    (quarterly statements return one column per period; the most
    recent period is column 0). Falls back to returning the input
    unchanged if it's already a scalar.

    This is the single place that used to be duplicated (and
    accidentally broken via .values instead of .iloc[0]) in four
    separate spots in app.py.
    """
    if hasattr(series_or_scalar, "iloc"):
        return series_or_scalar.iloc[0]
    return series_or_scalar


def _first_valid_ratio(statement, row_names, market_cap):
    """
    Walk row_names in order, return (ratio, found) for the first row
    that exists AND has a non-NaN value. If a row name exists but its
    value is NaN, keep trying the remaining row names instead of
    giving up (this was the break/NaN placement bug from earlier
    iterations).
    """
    for row in row_names:
        if row in statement.index:
            val = _get_latest_value(statement.loc[row])
            if not pd.isna(val) and val is not None:
                return (float(val) / market_cap) * 100, True
    return None, False


def calculate_debt_ratio(balance_sheet, market_cap):
    if "Total Debt" not in balance_sheet.index:
        return None
    val = _get_latest_value(balance_sheet.loc["Total Debt"])
    if pd.isna(val) or val is None:
        return None
    return (float(val) / market_cap) * 100


def calculate_interest_ratio(financials):
    """
    Returns None (not 0) when the interest-income line is simply
    absent from the statement — absence of data must never be
    silently treated as "zero interest income, therefore compliant".
    """
    total_revenue = None
    for row in REVENUE_ROW_NAMES:
        if row in financials.index:
            val = _get_latest_value(financials.loc[row])
            if not pd.isna(val) and float(val) > 0:
                total_revenue = float(val)
                break
    if total_revenue is None:
        return None

    interest_income = 0.0
    found_interest_row = False
    for row in INTEREST_INCOME_ROW_NAMES:
        if row in financials.index:
            val = _get_latest_value(financials.loc[row])
            if not pd.isna(val) and val is not None:
                interest_income += float(val)
                found_interest_row = True

    if not found_interest_row:
        return None

    return (interest_income / total_revenue) * 100


def calculate_cash_ratio(balance_sheet, market_cap):
    ratio, _ = _first_valid_ratio(balance_sheet, CASH_ROW_NAMES, market_cap)
    return ratio


def calculate_receivables_ratio(balance_sheet, market_cap):
    ratio, _ = _first_valid_ratio(balance_sheet, RECEIVABLES_ROW_NAMES, market_cap)
    return ratio


def determine_compliance(debt_ratio, interest_ratio, cash_ratio, receivables_ratio):
    """
    Returns one of "COMPLIANT", "NON-COMPLIANT", "INSUFFICIENT DATA".
    Missing data always wins over a pass/fail verdict — never guess.
    """
    ratios = [debt_ratio, interest_ratio, cash_ratio, receivables_ratio]
    if any(r is None for r in ratios):
        return "INSUFFICIENT DATA"

    debt_pass = debt_ratio <= DEBT_THRESHOLD
    interest_pass = interest_ratio <= INTEREST_THRESHOLD
    cash_pass = cash_ratio <= CASH_THRESHOLD
    receivables_pass = receivables_ratio <= RECEIVABLES_THRESHOLD

    if debt_pass and interest_pass and cash_pass and receivables_pass:
        return "COMPLIANT"
    return "NON-COMPLIANT"


def screen_company(balance_sheet, financials, market_cap):
    """
    Convenience wrapper: runs all four filters and the final decision
    for one company, returning a plain dict ready to display or export.
    """
    debt_ratio = calculate_debt_ratio(balance_sheet, market_cap)
    interest_ratio = calculate_interest_ratio(financials)
    cash_ratio = calculate_cash_ratio(balance_sheet, market_cap)
    receivables_ratio = calculate_receivables_ratio(balance_sheet, market_cap)

    status = determine_compliance(debt_ratio, interest_ratio, cash_ratio, receivables_ratio)

    return {
        "debt_ratio": debt_ratio,
        "debt_pass": debt_ratio is not None and debt_ratio <= DEBT_THRESHOLD,
        "interest_ratio": interest_ratio,
        "interest_pass": interest_ratio is not None and interest_ratio <= INTEREST_THRESHOLD,
        "cash_ratio": cash_ratio,
        "cash_pass": cash_ratio is not None and cash_ratio <= CASH_THRESHOLD,
        "receivables_ratio": receivables_ratio,
        "receivables_pass": receivables_ratio is not None and receivables_ratio <= RECEIVABLES_THRESHOLD,
        "status": status,
    }
