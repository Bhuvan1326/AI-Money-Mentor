# fire_calculator.py — FIRE corpus & timeline (offline)
"""
FIRE corpus (rule specified): monthly_expenses × 25 × 12
  = 25 × annual expenses (classic 4% rule shorthand).
"""

from __future__ import annotations

from dataclasses import dataclass

from financial_calculator import calculate_sip_future_value, sip_required_for_target
from utils import safe_float


@dataclass
class FIREResult:
    fire_corpus: float
    annual_expenses: float
    monthly_expenses: float
    age_now: int
    years_to_fire: float | None
    retire_at_age: float | None
    monthly_investment_needed: float  # SIP to reach corpus in remaining_working_years (if set)
    assumed_return_pct: float
    message: str


def years_until_net_worth(
    starting: float,
    monthly_contrib: float,
    target: float,
    annual_return_pct: float = 10.0,
    max_months: int = 600,
) -> float | None:
    """Deterministic month-by-month growth; returns years or None if not reached."""
    nw = safe_float(starting)
    c = max(0.0, safe_float(monthly_contrib))
    r = safe_float(annual_return_pct) / 100.0 / 12.0
    tgt = safe_float(target)
    if tgt <= 0:
        return 0.0
    for m in range(max_months + 1):
        if nw >= tgt:
            return m / 12.0
        nw = nw * (1.0 + r) + c
    return None


def compute_fire(
    age: int,
    monthly_income: float,
    monthly_expenses: float,
    current_savings: float,
    monthly_investments: float,
    max_age: int = 70,
    assumed_return_pct: float = 10.0,
) -> FIREResult:
    """
    - fire_corpus = monthly_expenses * 25 * 12
    - years_to_fire from current savings + monthly_investments
    - monthly_investment_needed to hit corpus by (max_age - age) if timeline not met organically
    """
    me = max(0.0, safe_float(monthly_expenses))
    annual_exp = me * 12.0
    corpus = me * 25.0 * 12.0  # same as 25 × annual expenses

    inc = safe_float(monthly_income)
    contrib = max(0.0, safe_float(monthly_investments))
    # If user saves nothing but has surplus, optional boost: not assumed — use declared SIP only
    liquid = max(0.0, safe_float(current_savings))

    ytf = years_until_net_worth(liquid, contrib, corpus, assumed_return_pct)
    retire_age = (age + ytf) if ytf is not None else None

    working_years_left = max(1, max_age - int(age))
    shortfall = max(0.0, corpus - liquid)
    sip_to_hit = sip_required_for_target(shortfall, assumed_return_pct, float(working_years_left))
    if ytf is not None:
        msg = (
            f"At ~{assumed_return_pct}% nominal return and your current SIP, "
            f"you could reach the FIRE corpus in about **{ytf:.1f} years**."
        )
    else:
        msg = (
            f"With current inputs, the FIRE corpus may not be reached within the projection window — "
            f"consider increasing investments toward **{sip_to_hit:,.0f}**/month (illustrative) over {working_years_left} years."
        )
    return FIREResult(
        fire_corpus=float(corpus),
        annual_expenses=float(annual_exp),
        monthly_expenses=float(me),
        age_now=int(age),
        years_to_fire=float(ytf) if ytf is not None else None,
        retire_at_age=float(retire_age) if retire_age is not None else None,
        monthly_investment_needed=float(sip_to_hit),
        assumed_return_pct=float(assumed_return_pct),
        message=msg,
    )


def fire_corpus_only(monthly_expenses: float) -> float:
    me = max(0.0, safe_float(monthly_expenses))
    return float(me * 25.0 * 12.0)
