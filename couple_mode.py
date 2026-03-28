"""Offline heuristics for two-earner households."""

from __future__ import annotations

from dataclasses import dataclass

from financial_calculator import UserFinancialProfile, monthly_savings_rate
from joint_calculator import JointHouseholdMeta
from risk_profile import RiskProfileOutcome, allocation_for_label
from utils import clamp, safe_float


def detect_couple_risk_profile(
    partner_a_age: int,
    partner_b_age: int,
    monthly_income: float,
    monthly_emi: float,
    monthly_expenses: float,
) -> RiskProfileOutcome:
    """
    Couple rules:
      - High EMI vs income → Conservative
      - One partner meaningfully older or large age gap → Moderate
      - Both relatively young → Aggressive
      Otherwise Moderate.
    """
    inc = safe_float(monthly_income)
    emi = safe_float(monthly_emi)
    dti = (emi / inc * 100.0) if inc > 0 else 0.0
    age_a, age_b = int(partner_a_age), int(partner_b_age)
    sr = monthly_savings_rate(inc, safe_float(monthly_expenses))

    if dti > 35:
        label = "Conservative"
        why = "Joint EMI load is elevated relative to household income — prioritize stability and debt runway."
    elif max(age_a, age_b) >= 47 or abs(age_a - age_b) > 12:
        label = "Moderate"
        why = "Age mix or gap suggests a moderated glidepath rather than maximum equity."
    elif min(age_a, age_b) < 36 and max(age_a, age_b) < 45:
        label = "Aggressive"
        why = "Both partners are relatively young — longer joint horizon can support higher equity (if behaviour matches risk)."
    else:
        label = "Moderate"
        why = "Balanced default for a working couple — refine with actual goal dates and cash buffers."

    alloc = allocation_for_label(label.lower())
    score = 50.0 + (10 if label == "Aggressive" else 0) - (15 if label == "Conservative" else 0)
    score = clamp(score + (sr / 50.0 * 10.0), 15.0, 95.0)

    # Horizon placeholder: use older partner age as rough anchor
    horizon = max(5, 65 - max(age_a, age_b))

    rationale = [
        f"Joint EMI to income ≈ **{dti:.0f}%**.",
        f"Partner ages **{age_a}** & **{age_b}** — {why}",
        f"Template allocation: **{alloc.equity_pct}/{alloc.debt_pct}/{alloc.gold_pct}** equity/debt/gold.",
    ]
    return RiskProfileOutcome(
        label=label,
        score=round(score, 1),
        horizon_years=horizon,
        savings_rate_pct=round(sr, 2),
        stability_note="Household risk view — align term insurance and health cover to **both** incomes.",
        allocation=alloc,
        rationale=rationale,
    )


def joint_financial_advice_lines(meta: JointHouseholdMeta) -> list[str]:
    """Short bullet ideas for Indian couples (education only)."""
    lines = [
        "**Tax:** Split **80C / 80D / NPS** optimally — higher marginal partner often benefits more from deductions (verify with a CA).",
        "**SIPs:** Run **two mandates** or split one folio logically so both partners see forced savings.",
        "**Emergency fund:** Target **6–9× combined monthly expenses** in joint + individual liquid access.",
        "**Insurance:** **Term + health** sized to loss of either income; disclose medical history accurately.",
    ]
    if meta.share_a_pct > 70 or meta.share_b_pct > 70:
        lines.append(
            "**Income skew:** One partner carries most income — build buffers and skill diversification if primary earner pauses work."
        )
    return lines


@dataclass
class CoupleAdviceBundle:
    """Passed into offline AI for richer joint context."""

    meta: JointHouseholdMeta
    risk: RiskProfileOutcome
    advice_lines: list[str]


def build_couple_bundle(
    meta: JointHouseholdMeta,
    household_profile: UserFinancialProfile,
) -> CoupleAdviceBundle:
    risk = detect_couple_risk_profile(
        meta.partner_a_age,
        meta.partner_b_age,
        household_profile.monthly_income,
        household_profile.existing_debt_emi,
        household_profile.monthly_expenses,
    )
    return CoupleAdviceBundle(
        meta=meta,
        risk=risk,
        advice_lines=joint_financial_advice_lines(meta),
    )
