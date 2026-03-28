# financial_score.py — Money Health Score (0–100), hackathon dashboard metric
"""Combines savings, emergency coverage, investing discipline, and debt load."""

from __future__ import annotations

from dataclasses import dataclass

from financial_calculator import UserFinancialProfile
from utils import clamp, safe_float


@dataclass
class MoneyHealthResult:
    score: float
    band: str  # Excellent | Good | Needs Improvement
    savings_ratio_pct: float
    emergency_coverage_pct: float  # liquid vs 6× expenses
    investment_intensity_pct: float  # SIP / income
    debt_ratio_pct: float  # EMI / income
    breakdown: dict[str, float]


def money_health_band(score: float) -> str:
    if score >= 80:
        return "Excellent"
    if score >= 60:
        return "Good"
    return "Needs Improvement"


def calculate_money_health(
    profile: UserFinancialProfile,
    emergency_months: int = 6,
) -> MoneyHealthResult:
    """
    Score from four pillars (each 0–100 sub-score, weighted):
      - Savings ratio (income - expenses) / income
      - Emergency fund: current_savings vs emergency_months × expenses
      - Investment amount: monthly_investments / income
      - Debt ratio: EMI / income (lower is better)
    """
    income = safe_float(profile.monthly_income)
    expenses = safe_float(profile.monthly_expenses)
    savings_liquid = safe_float(profile.current_savings)
    invest = safe_float(profile.monthly_investments)
    emi = safe_float(profile.existing_debt_emi)

    sr = clamp((income - expenses) / income * 100.0, 0.0, 100.0) if income > 0 else 0.0
    target_ef = max(1.0, safe_float(emergency_months) * expenses)
    ec = clamp(savings_liquid / target_ef * 100.0, 0.0, 150.0)  # allow >100 for buffer
    ec_capped = min(100.0, ec)  # score component capped at 100

    inv_pct = clamp(invest / income * 100.0, 0.0, 100.0) if income > 0 else 0.0

    dti = clamp(emi / income * 100.0, 0.0, 100.0) if income > 0 else 0.0
    debt_score = clamp(100.0 - dti * 1.5, 0.0, 100.0)  # 0 DTI → 100; ~67% DTI → 0

    # Sub-scores 0–100
    s_save = clamp(sr / 35.0 * 100.0, 0.0, 100.0)  # 35%+ savings rate maxes
    s_emer = clamp(ec_capped, 0.0, 100.0)
    s_inv = clamp(inv_pct / 25.0 * 100.0, 0.0, 100.0)  # 25%+ of income invested maxes
    s_debt = debt_score

    w_save, w_emer, w_inv, w_debt = 0.28, 0.28, 0.24, 0.20
    score = w_save * s_save + w_emer * s_emer + w_inv * s_inv + w_debt * s_debt
    score = round(clamp(score, 0.0, 100.0), 1)

    band = money_health_band(score)
    breakdown = {
        "savings_pillar": round(s_save, 1),
        "emergency_pillar": round(s_emer, 1),
        "investment_pillar": round(s_inv, 1),
        "debt_pillar": round(s_debt, 1),
    }
    return MoneyHealthResult(
        score=score,
        band=band,
        savings_ratio_pct=round(sr, 2),
        emergency_coverage_pct=round(ec, 2),
        investment_intensity_pct=round(inv_pct, 2),
        debt_ratio_pct=round(dti, 2),
        breakdown=breakdown,
    )
