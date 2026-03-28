# personality.py — Financial personality heuristic (Saver / Spender / Investor)
"""Uses savings rate and expense intensity; lightweight hackathon badge."""

from __future__ import annotations

from dataclasses import dataclass

from financial_calculator import monthly_savings_rate
from utils import safe_float


@dataclass
class PersonalityResult:
    personality: str  # Saver | Spender | Investor
    tagline: str
    savings_rate_pct: float
    invest_to_income_pct: float
    expense_to_income_pct: float


def detect_personality(
    monthly_income: float,
    monthly_expenses: float,
    monthly_investments: float,
) -> PersonalityResult:
    inc = safe_float(monthly_income)
    exp = safe_float(monthly_expenses)
    inv = safe_float(monthly_investments)
    sr = monthly_savings_rate(inc, exp)
    eti = (exp / inc * 100.0) if inc > 0 else 0.0
    iti = (inv / inc * 100.0) if inc > 0 else 0.0

    # Priority: strong investor signal → Investor; high spend + low save → Spender; else Saver tendencies
    if iti >= 12 and sr >= 12:
        p = "Investor"
        tag = "You direct a healthy slice of income into markets — keep rebalancing and emergency liquidity."
    elif iti >= 8 and sr >= 8:
        p = "Investor"
        tag = "You’re building investing muscle — scale SIPs as income grows and avoid timing the market."
    elif eti >= 78 or sr < 8:
        p = "Spender"
        tag = "Cash flow tilts toward consumption — small automated savings rules can shift trajectory fast."
    elif sr >= 22 and eti <= 65:
        p = "Saver"
        tag = "You preserve capital well — next step is purposeful investing beyond idle savings."
    else:
        p = "Saver"
        tag = "Balanced day-to-day choices with room to optimize investing and discretionary spend."

    return PersonalityResult(
        personality=p,
        tagline=tag,
        savings_rate_pct=round(sr, 2),
        invest_to_income_pct=round(iti, 2),
        expense_to_income_pct=round(eti, 2),
    )
