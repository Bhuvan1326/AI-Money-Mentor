# expense_analyzer.py — Spending stress signals + coaching tips (offline)
"""Flags overspending, low savings, high EMI; returns structured suggestions."""

from __future__ import annotations

from dataclasses import dataclass

from financial_calculator import monthly_savings_rate
from utils import safe_float


@dataclass
class ExpenseAnalysis:
    flags: list[str]
    suggestions: list[str]
    savings_rate_pct: float
    expense_to_income_pct: float
    emi_to_income_pct: float


def analyze_expenses(
    monthly_income: float,
    monthly_expenses: float,
    monthly_emi: float,
    monthly_investments: float = 0.0,
) -> ExpenseAnalysis:
    inc = safe_float(monthly_income)
    exp = safe_float(monthly_expenses)
    emi = safe_float(monthly_emi)
    inv = safe_float(monthly_investments)

    sr = monthly_savings_rate(inc, exp)
    eti = (exp / inc * 100.0) if inc > 0 else 0.0
    dti = (emi / inc * 100.0) if inc > 0 else 0.0

    flags: list[str] = []
    if inc > 0 and exp > inc:
        flags.append("Deficit cash flow — expenses exceed income.")
    elif inc > 0 and eti > 90:
        flags.append("Very thin margin — expenses consume over 90% of income.")
    elif inc > 0 and eti > 75:
        flags.append("High fixed lifestyle load — little room for surprises.")

    if sr < 10:
        flags.append("Low savings rate relative to income.")
    if dti > 40:
        flags.append("High EMI burden vs income.")
    elif dti > 25:
        flags.append("Elevated EMI share — stress-test a 3-month income drop.")

    if inc > 0 and inv < inc * 0.05 and sr >= 10:
        flags.append("Limited visible investing — surplus may be idle in savings.")

    sugg: list[str] = []
    if "Deficit" in "".join(flags) or exp > inc:
        sugg.append("Pause discretionary spending; list top 5 expense merchants; consider income bridge options.")
    if eti > 75:
        sugg.append("Try a 30-day expense log; cancel unused subscriptions; renegotiate insurance/telecom.")
    if sr < 15:
        sugg.append("Set one automatic transfer: even ₹2,000–5,000/mo into a liquid fund builds habit.")
    if dti > 40:
        sugg.append("Prioritize prepayment of highest-interest debt; avoid new EMIs until DTI < ~30%.")
    if not sugg:
        sugg.append("Cash flow looks manageable — increase SIPs yearly and keep 6+ months emergency liquidity.")

    return ExpenseAnalysis(
        flags=flags,
        suggestions=sugg,
        savings_rate_pct=round(sr, 2),
        expense_to_income_pct=round(eti, 2),
        emi_to_income_pct=round(dti, 2),
    )
