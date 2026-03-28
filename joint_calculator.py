# joint_calculator.py — Combine Partner A + B into one household UserFinancialProfile
"""
Liquid savings = partner1 + partner2 (corpus).
Monthly surplus flow = total income − total expenses (for reference, not stored as current_savings).
"""

from __future__ import annotations

from dataclasses import dataclass

from financial_calculator import UserFinancialProfile
from utils import safe_float, safe_int


@dataclass
class PartnerInputs:
    age: int
    retirement_age: int
    monthly_income: float
    monthly_expenses: float
    liquid_savings: float
    monthly_sip: float
    monthly_emi: float


@dataclass
class JointHouseholdMeta:
    """Extra facts for couple UI (retirement sequencing, flows)."""

    total_income: float
    total_expenses: float
    liquid_corpus: float
    total_sip: float
    total_emi: float
    monthly_surplus_flow: float  # income − expenses (household cashflow)
    partner_a_income: float
    partner_b_income: float
    partner_a_age: int
    partner_b_age: int
    years_to_first_retirement: int
    first_retirer: str  # "A" or "B"
    share_a_pct: float
    share_b_pct: float


def _years_to_retirement(p: PartnerInputs) -> int:
    return max(0, int(p.retirement_age) - int(p.age))


def combine_household(partner_a: PartnerInputs, partner_b: PartnerInputs) -> JointHouseholdMeta:
    inc_a, inc_b = safe_float(partner_a.monthly_income), safe_float(partner_b.monthly_income)
    exp_a, exp_b = safe_float(partner_a.monthly_expenses), safe_float(partner_b.monthly_expenses)
    sip_a, sip_b = safe_float(partner_a.monthly_sip), safe_float(partner_b.monthly_sip)
    emi_a, emi_b = safe_float(partner_a.monthly_emi), safe_float(partner_b.monthly_emi)
    liq_a, liq_b = safe_float(partner_a.liquid_savings), safe_float(partner_b.liquid_savings)

    ti = inc_a + inc_b
    te = exp_a + exp_b
    tsip = sip_a + sip_b
    temi = emi_a + emi_b
    liq = liq_a + liq_b
    surplus = ti - te

    ya, yb = _years_to_retirement(partner_a), _years_to_retirement(partner_b)
    if ya <= yb:
        first, yfr = "A", ya
    else:
        first, yfr = "B", yb

    tot_inc = ti if ti > 0 else 1.0
    return JointHouseholdMeta(
        total_income=ti,
        total_expenses=te,
        liquid_corpus=liq,
        total_sip=tsip,
        total_emi=temi,
        monthly_surplus_flow=surplus,
        partner_a_income=inc_a,
        partner_b_income=inc_b,
        partner_a_age=int(partner_a.age),
        partner_b_age=int(partner_b.age),
        years_to_first_retirement=max(0, int(yfr)),
        first_retirer=first,
        share_a_pct=round(inc_a / tot_inc * 100.0, 1),
        share_b_pct=round(inc_b / tot_inc * 100.0, 1),
    )


def build_couple_user_profile(
    partner_a: PartnerInputs,
    partner_b: PartnerInputs,
    *,
    income_stability: str,
    financial_goal: str,
    goal_amount: float,
    goal_years: int,
) -> tuple[UserFinancialProfile, JointHouseholdMeta]:
    """
    Map household → single UserFinancialProfile so all existing calculators run unchanged.
    Uses average age and earliest target retirement age, with retirement_age ≥ avg_age + 1.
    """
    meta = combine_household(partner_a, partner_b)
    avg_age = int(round((meta.partner_a_age + meta.partner_b_age) / 2.0))
    earliest_r = min(int(partner_a.retirement_age), int(partner_b.retirement_age))
    ret_age = max(earliest_r, avg_age + 1)

    prof = UserFinancialProfile(
        age=avg_age,
        retirement_age=ret_age,
        monthly_income=meta.total_income,
        monthly_expenses=meta.total_expenses,
        current_savings=meta.liquid_corpus,
        monthly_investments=meta.total_sip,
        existing_debt_emi=meta.total_emi,
        income_stability=income_stability,
        financial_goal=financial_goal,
        goal_amount=float(goal_amount),
        goal_years=int(goal_years),
    )
    return prof, meta
