# risk_profile.py — Conservative / Moderate / Aggressive + allocation engine
"""Uses age, savings rate, income stability, and investment horizon."""

from __future__ import annotations

from dataclasses import dataclass

from financial_calculator import UserFinancialProfile, monthly_savings_rate
from utils import clamp, safe_float, safe_int


@dataclass
class AllocationBreakdown:
    equity_pct: int
    debt_pct: int
    gold_pct: int


@dataclass
class RiskProfileOutcome:
    label: str  # Conservative | Moderate | Aggressive
    score: float  # internal 0–100 (higher → more risk capacity)
    horizon_years: int
    savings_rate_pct: float
    stability_note: str
    allocation: AllocationBreakdown
    rationale: list[str]


def allocation_for_label(label: str) -> AllocationBreakdown:
    """FEATURE 8 — fixed template bands."""
    l = (label or "").strip().lower()
    if l == "aggressive":
        return AllocationBreakdown(70, 20, 10)
    if l == "conservative":
        return AllocationBreakdown(40, 40, 20)
    # default Moderate
    return AllocationBreakdown(60, 30, 10)


def _stability_score(stability: str) -> float:
    s = (stability or "stable").lower().replace(" ", "_")
    if s in ("variable", "unstable", "volatile"):
        return 20.0
    if s in ("somewhat_variable", "somewhat variable", "mixed"):
        return 50.0
    return 85.0  # stable


def detect_risk_profile_v2(profile: UserFinancialProfile) -> RiskProfileOutcome:
    age = safe_int(profile.age, 30)
    ret_age = safe_int(profile.retirement_age, 60)
    horizon = max(1, ret_age - age)
    sr = monthly_savings_rate(safe_float(profile.monthly_income), safe_float(profile.monthly_expenses))
    inc = safe_float(profile.monthly_income)
    emi = safe_float(profile.existing_debt_emi)
    dti = (emi / inc * 100.0) if inc > 0 else 0.0

    stab = _stability_score(profile.income_stability)

    # Base score: young + long horizon + high savings + stable income − debt stress
    score = 45.0
    if age < 35:
        score += 12
    elif age < 45:
        score += 6
    if horizon >= 20:
        score += 12
    elif horizon >= 10:
        score += 6
    if sr >= 25:
        score += 15
    elif sr >= 15:
        score += 8
    score += stab * 0.15
    score -= clamp(dti * 0.8, 0.0, 25.0)
    if safe_float(profile.monthly_expenses) > inc * 0.92:
        score -= 12
    score = clamp(score, 0.0, 100.0)

    if score < 42:
        label = "Conservative"
    elif score < 68:
        label = "Moderate"
    else:
        label = "Aggressive"

    alloc = allocation_for_label(label)
    stab_note = {
        "stable": "Income treated as stable — supports modest risk if horizon is long.",
        "somewhat_variable": "Somewhat variable income — keep higher liquidity / debt cushion.",
        "variable": "Variable income — favour conservative glidepath until buffer is strong.",
    }.get(
        (profile.income_stability or "stable").lower().replace(" ", "_"),
        "Review stability assumptions annually.",
    )

    rationale = [
        f"Investment horizon ~{horizon} years (to target retirement age).",
        f"Savings rate ~{sr:.1f}% of income; EMI load ~{dti:.0f}% of income.",
        f"Income stability factor influences ability to stay invested through volatility.",
    ]
    return RiskProfileOutcome(
        label=label,
        score=round(score, 1),
        horizon_years=horizon,
        savings_rate_pct=round(sr, 2),
        stability_note=stab_note,
        allocation=alloc,
        rationale=rationale,
    )
