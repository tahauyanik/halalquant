"""
test_filters.py

Run with:  pytest test_filters.py

These tests exist because the same three bugs kept reappearing across
different versions of app.py during development:
  1. Using .values instead of .iloc[0]  -> crashes on multi-row Series
  2. Missing data silently treated as 0 -> false "compliant" results
  3. `break` placed outside the NaN check -> skips valid fallback rows

Run this file before every GitHub push. If it passes, the core
screening math has not regressed.
"""

import pandas as pd
import pytest

from screening_logic import (
    calculate_debt_ratio,
    calculate_interest_ratio,
    calculate_cash_ratio,
    calculate_receivables_ratio,
    determine_compliance,
    screen_company,
    DEBT_THRESHOLD,
    INTEREST_THRESHOLD,
)


def make_statement(rows: dict):
    """
    Build a minimal one-column DataFrame shaped like yfinance's
    quarterly_balance_sheet / quarterly_financials output: row names
    as the index, one column per reporting period (most recent first).
    """
    return pd.DataFrame(rows, index=[pd.Timestamp("2026-06-30")]).T


# --- Debt ratio ---------------------------------------------------

def test_debt_ratio_normal_case():
    bs = make_statement({"Total Debt": 3300})
    assert calculate_debt_ratio(bs, market_cap=10000) == pytest.approx(33.0)


def test_debt_ratio_missing_row_returns_none():
    bs = make_statement({"Something Else": 100})
    assert calculate_debt_ratio(bs, market_cap=10000) is None


def test_debt_ratio_nan_value_returns_none_not_zero():
    bs = make_statement({"Total Debt": float("nan")})
    assert calculate_debt_ratio(bs, market_cap=10000) is None


# --- Interest ratio ------------------------------------------------

def test_interest_ratio_normal_case():
    fin = make_statement({"Total Revenue": 1000, "Interest Income": 50})
    assert calculate_interest_ratio(fin) == pytest.approx(5.0)


def test_interest_ratio_missing_row_is_insufficient_not_zero():
    """
    The historical bug: a company with no Interest Income line at all
    must be treated as "insufficient data", never silently as 0%
    (which would wrongly mark it as passing the interest filter).
    """
    fin = make_statement({"Total Revenue": 1000})
    assert calculate_interest_ratio(fin) is None


def test_interest_ratio_uses_operating_revenue_fallback():
    fin = make_statement({"Operating Revenue": 2000, "Interest Income": 20})
    assert calculate_interest_ratio(fin) == pytest.approx(1.0)


def test_interest_ratio_sums_multiple_matching_rows():
    fin = make_statement({
        "Total Revenue": 1000,
        "Interest Income": 10,
        "Non Operating Interest Income": 5,
    })
    assert calculate_interest_ratio(fin) == pytest.approx(1.5)


# --- Cash ratio: the break/NaN regression test ---------------------

def test_cash_ratio_falls_back_when_first_row_is_nan():
    """
    Regression test for the break-placement bug: if the first
    candidate row name exists but its value is NaN, the function must
    still try the next candidate row name rather than giving up.
    """
    bs = make_statement({
        "Cash And Cash Equivalents": float("nan"),
        "Cash Cash Equivalents And Short Term Investments": 500,
    })
    assert calculate_cash_ratio(bs, market_cap=10000) == pytest.approx(5.0)


def test_cash_ratio_missing_entirely_returns_none():
    bs = make_statement({"Total Debt": 100})
    assert calculate_cash_ratio(bs, market_cap=10000) is None


# --- Receivables ratio ----------------------------------------------

def test_receivables_ratio_falls_back_when_first_row_is_nan():
    bs = make_statement({
        "Receivables": float("nan"),
        "Accounts Receivable": 200,
    })
    assert calculate_receivables_ratio(bs, market_cap=10000) == pytest.approx(2.0)


# --- Compliance decision --------------------------------------------

def test_compliance_all_pass():
    assert determine_compliance(10, 2, 10, 10) == "COMPLIANT"


def test_compliance_one_ratio_fails():
    assert determine_compliance(40, 2, 10, 10) == "NON-COMPLIANT"


def test_compliance_missing_data_beats_pass_fail():
    """Missing data must never be silently upgraded to a verdict."""
    assert determine_compliance(10, None, 10, 10) == "INSUFFICIENT DATA"


def test_thresholds_are_the_documented_values():
    """Guards against someone quietly changing the screening thresholds."""
    assert DEBT_THRESHOLD == 33
    assert INTEREST_THRESHOLD == 5


# --- End-to-end wrapper ----------------------------------------------

def test_screen_company_end_to_end_compliant():
    bs = make_statement({
        "Total Debt": 1000,
        "Cash And Cash Equivalents": 500,
        "Receivables": 300,
    })
    fin = make_statement({
        "Total Revenue": 10000,
        "Interest Income": 100,
    })
    result = screen_company(bs, fin, market_cap=10000)
    assert result["status"] == "COMPLIANT"
    assert result["debt_pass"] is True
    assert result["interest_pass"] is True


def test_screen_company_end_to_end_insufficient_data():
    bs = make_statement({"Total Debt": 1000})  # no cash / receivables rows
    fin = make_statement({"Total Revenue": 10000, "Interest Income": 100})
    result = screen_company(bs, fin, market_cap=10000)
    assert result["status"] == "INSUFFICIENT DATA"
