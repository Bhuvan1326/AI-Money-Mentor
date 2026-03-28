# financial_calculator.py — Core financial logic (India-focused)
"""SIP, retirement, FIRE, health score, risk, emergency fund, tax hints, goals."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from utils import clamp, safe_float, safe_int


@dataclass
class UserFinancialProfile:
    age: int = 30
    retirement_age: int = 60
    monthly_income: float = 100_000.0
    monthly_expenses: float = 60_000.0
    current_savings: float = 500_000.0
    monthly_investments: float = 15_000.0
    existing_debt_emi: float = 0.0
    # For risk models: "stable" | "somewhat_variable" | "variable"
    income_stability: str = "stable"
    financial_goal: str = "retirement"  # house, car, retirement, emergency
    goal_amount: float = 2_000_000.0
    goal_years: int = 10


@dataclass
class HealthScoreResult:
    score: float
    label: str
    factors: dict[str, float]
    tips: list[str]


@dataclass
class SIPResult:
    monthly_sip: float
    annual_rate: float
    years: int
    future_value: float
    total_invested: float
    gains: float


@dataclass
class RetirementResult:
    years_to_retire: int
    monthly_expense_at_retirement: float
    corpus_needed: float  # simplified real-return annuity
    monthly_sip_to_reach: float
    fire_number: float
    years_to_fire: float | None  # optional, if achievable


@dataclass
class EmergencyFundResult:
    recommended_months: int
    target_amount: float
    current_gap: float
    message: str


@dataclass
class RiskProfileResult:
    level: str  # low, medium, high
    score: float
    equity_allocation: tuple[int, int]  # min, max %
    rationale: list[str]


def monthly_savings_rate(income: float, expenses: float) -> float:
    if income <= 0:
        return 0.0
    return clamp((income - expenses) / income * 100.0, 0.0, 100.0)


def calculate_sip_future_value(
    monthly_sip: float,
    annual_return_pct: float = 12.0,
    years: float = 10.0,
) -> SIPResult:
    """
    Future value of monthly SIP at end of each month (ordinary annuity).
    FV = P * [((1 + r)^n - 1) / r], r = monthly rate, n = months.
    """
    monthly_sip = safe_float(monthly_sip)
    r_annual = safe_float(annual_return_pct) / 100.0
    r = r_annual / 12.0
    n = int(round(safe_float(years) * 12))
    if n <= 0:
        return SIPResult(monthly_sip, annual_return_pct, 0, 0.0, 0.0, 0.0)
    if r <= 0:
        fv = monthly_sip * n
    else:
        fv = monthly_sip * (((1 + r) ** n - 1) / r)
    invested = monthly_sip * n
    return SIPResult(
        monthly_sip=monthly_sip,
        annual_rate=annual_return_pct,
        years=int(round(years)),
        future_value=float(fv),
        total_invested=float(invested),
        gains=float(fv - invested),
    )


def sip_required_for_target(
    target_corpus: float,
    annual_return_pct: float = 12.0,
    years: float = 10.0,
) -> float:
    """Monthly SIP needed to reach target_corpus."""
    target_corpus = safe_float(target_corpus)
    r_annual = safe_float(annual_return_pct) / 100.0
    r = r_annual / 12.0
    n = int(round(safe_float(years) * 12))
    if n <= 0 or target_corpus <= 0:
        return 0.0
    if r <= 0:
        return target_corpus / n
    return target_corpus / (((1 + r) ** n - 1) / r)


def retirement_corpus_needed(
    monthly_expenses_today: float,
    years_to_retirement: int,
    years_in_retirement: int = 25,
    inflation_annual: float = 6.0,
    post_ret_return: float = 7.0,
) -> float:
    """
    Corpus at retirement using inflation-adjusted expenses and
    present value of retirement-phase annuity (real simplified model).
    """
    me = safe_float(monthly_expenses_today)
    inf = safe_float(inflation_annual) / 100.0
    pr = safe_float(post_ret_return) / 100.0
    ytr = max(1, safe_int(years_to_retirement))
    yir = max(1, safe_int(years_in_retirement))

    annual_exp_retire = me * 12 * ((1 + inf) ** ytr)
    # Monthly withdrawal from corpus at start of retirement: use annuity factor
    monthly_need = annual_exp_retire / 12.0
    rm = pr / 12.0
    months = yir * 12
    if rm <= 0:
        return monthly_need * months
    # PV of monthly withdrawals growing with inflation — simplified: flat real return
    # Corpus such that 4% rule style: corpus * safe_draw = annual need
    safe_draw = 0.04
    if pr > inf:
        real_r = (1 + pr) / (1 + inf) - 1.0
        if real_r > 0:
            corpus = annual_exp_retire / real_r * (1 - (1 + real_r) ** (-yir))
        else:
            corpus = annual_exp_retire * yir
    else:
        corpus = annual_exp_retire / safe_draw
    return float(max(corpus, monthly_need * 12 * 5))


def fire_number(
    annual_expenses: float,
    withdrawal_rate: float = 0.04,
) -> float:
    """FIRE corpus = annual expenses / withdrawal_rate (default 4%)."""
    ae = safe_float(annual_expenses)
    wr = clamp(safe_float(withdrawal_rate), 0.01, 0.15)
    return float(ae / wr)


def years_to_fire_estimate(
    current_savings: float,
    monthly_income: float,
    monthly_expenses: float,
    expected_return_annual: float = 10.0,
    fire_corpus: float = 0.0,
) -> float | None:
    """Project years until net worth reaches FIRE number (deterministic simulation)."""
    if fire_corpus <= 0:
        return None
    nw = safe_float(current_savings)
    inc = safe_float(monthly_income)
    exp = safe_float(monthly_expenses)
    monthly_save = max(0.0, inc - exp)
    r = safe_float(expected_return_annual) / 100.0 / 12.0
    max_months = 600  # 50 years cap
    for m in range(max_months):
        if nw >= fire_corpus:
            return m / 12.0
        nw = nw * (1 + r) + monthly_save
    return None


def calculate_money_health_score(profile: UserFinancialProfile) -> HealthScoreResult:
    """
    Composite 0–100 score: savings rate, emergency buffer, debt burden, invest vs surplus.
    """
    income = safe_float(profile.monthly_income)
    expenses = safe_float(profile.monthly_expenses)
    savings = safe_float(profile.current_savings)
    emi = safe_float(profile.existing_debt_emi)
    invest = safe_float(profile.monthly_investments)

    sr = monthly_savings_rate(income, expenses)
    months_buffer = (savings / expenses) if expenses > 0 else 12.0
    dti = (emi / income * 100.0) if income > 0 else 0.0
    surplus = max(0.0, income - expenses)
    invest_ratio = (invest / surplus * 100.0) if surplus > 0 else 0.0

    # Subscores 0–100
    s_savings = clamp(sr / 30.0 * 100.0, 0.0, 100.0)  # 30%+ savings = full
    s_buffer = clamp(months_buffer / 12.0 * 100.0, 0.0, 100.0)
    s_debt = clamp(100.0 - dti * 2.0, 0.0, 100.0)  # DTI 50% => 0
    s_invest = clamp(invest_ratio, 0.0, 100.0)

    weights = {"savings_rate": 0.30, "buffer": 0.25, "debt": 0.25, "investing": 0.20}
    score = (
        weights["savings_rate"] * s_savings
        + weights["buffer"] * s_buffer
        + weights["debt"] * s_debt
        + weights["investing"] * s_invest
    )
    score = round(clamp(score, 0.0, 100.0), 1)

    if score >= 75:
        label = "Strong"
    elif score >= 50:
        label = "Moderate"
    else:
        label = "Needs Focus"

    tips: list[str] = []
    if sr < 15:
        tips.append("Aim to save at least 15–20% of income after fixed costs.")
    if months_buffer < 6:
        tips.append("Build 6–12 months of expenses in liquid emergency fund.")
    if dti > 40:
        tips.append("High EMI burden: prioritize clearing high-interest debt.")
    if surplus > 0 and invest_ratio < 50:
        tips.append("Automate SIPs so a larger share of surplus is invested.")

    factors = {
        "savings_rate_pct": round(sr, 1),
        "emergency_months": round(months_buffer, 1),
        "dti_pct": round(dti, 1),
        "investment_of_surplus_pct": round(invest_ratio, 1),
    }
    return HealthScoreResult(score=score, label=label, factors=factors, tips=tips)


def emergency_fund_recommendation(profile: UserFinancialProfile) -> EmergencyFundResult:
    expenses = safe_float(profile.monthly_expenses)
    savings = safe_float(profile.current_savings)
    emi = safe_float(profile.existing_debt_emi)
    # More dependents / higher EMI => prefer higher months (simplified: use EMI)
    base_months = 6
    if emi > expenses * 0.3:
        base_months = 9
    months = min(12, base_months)
    target = expenses * months
    gap = max(0.0, target - savings)
    msg = (
        f"Target {months} months of expenses ({target:,.0f} INR) "
        f"in savings account or liquid funds."
    )
    return EmergencyFundResult(months, target, gap, msg)


def detect_risk_profile(profile: UserFinancialProfile) -> RiskProfileResult:
    """
    Heuristic risk score from age, horizon, savings stability, debt.
    """
    age = safe_int(profile.age, 30)
    ytr = max(1, safe_int(profile.retirement_age) - age)
    emi_ratio = (
        safe_float(profile.existing_debt_emi) / safe_float(profile.monthly_income)
        if profile.monthly_income
        else 0.0
    )
    score = 50.0
    if age < 35:
        score += 15
    if ytr > 15:
        score += 15
    if emi_ratio > 0.4:
        score -= 20
    if safe_float(profile.monthly_expenses) > safe_float(profile.monthly_income) * 0.9:
        score -= 15
    score = clamp(score, 0.0, 100.0)

    if score < 40:
        level = "low"
        equity = (20, 45)
    elif score < 70:
        level = "medium"
        equity = (45, 65)
    else:
        level = "high"
        equity = (65, 90)

    rationale = [
        f"Investment horizon ~{ytr} years to retirement.",
        f"Debt (EMI) load vs income: {emi_ratio*100:.0f}%.",
        "Higher equity suits longer horizons and lower near-term liquidity stress.",
    ]
    return RiskProfileResult(level=level, score=score, equity_allocation=equity, rationale=rationale)


def india_tax_saving_suggestions(annual_income: float) -> list[dict[str, Any]]:
    """India-specific pointers (not tax advice; for education)."""
    ai = safe_float(annual_income)
    suggestions = [
        {
            "section": "80C",
            "limit": "₹1.5 lakh",
            "ideas": "ELSS, PPF, EPF, life insurance premium, tuition fees, NSC, 5-year FD",
        },
        {
            "section": "80CCD(1B)",
            "limit": "₹50,000",
            "ideas": "Additional NPS contribution (beyond 80C)",
        },
        {
            "section": "80D",
            "limit": "₹25k–₹1L (depends on age/coverage)",
            "ideas": "Health insurance for self and parents",
        },
        {
            "section": "24(b)",
            "limit": "₹2 lakh interest",
            "ideas": "Home loan interest (conditions apply)",
        },
    ]
    if ai > 10_00_000:
        suggestions.append(
            {
                "section": "New tax regime vs old",
                "limit": "Compare",
                "ideas": "Use official calculator; old regime may help if 80C/80D used heavily.",
            }
        )
    return suggestions


def monthly_allocation_breakdown(
    monthly_income: float,
    monthly_expenses: float,
    risk_level: str,
) -> dict[str, float]:
    """Suggested split of surplus across goals (percentages of surplus)."""
    surplus = max(0.0, safe_float(monthly_income) - safe_float(monthly_expenses))
    if surplus <= 0:
        return {"emergency_topup": 0.0, "sip": 0.0, "goals": 0.0, "discretionary": 0.0}

    if risk_level == "high":
        sip_pct, em_pct = 0.55, 0.25
    elif risk_level == "medium":
        sip_pct, em_pct = 0.45, 0.30
    else:
        sip_pct, em_pct = 0.35, 0.35
    rest = 1.0 - sip_pct - em_pct
    goals_pct = rest * 0.6
    disc_pct = rest * 0.4
    return {
        "emergency_topup": round(em_pct * surplus, 2),
        "sip": round(sip_pct * surplus, 2),
        "goals": round(goals_pct * surplus, 2),
        "discretionary": round(disc_pct * surplus, 2),
    }


def wealth_projection_series(
    months: int,
    starting_savings: float,
    monthly_contribution: float,
    annual_return: float = 10.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Month-by-month projected net worth."""
    m = max(1, int(months))
    nw = safe_float(starting_savings)
    c = safe_float(monthly_contribution)
    r = safe_float(annual_return) / 100.0 / 12.0
    values = np.zeros(m + 1)
    values[0] = nw
    for i in range(1, m + 1):
        nw = nw * (1 + r) + c
        values[i] = nw
    months_axis = np.arange(0, m + 1)
    return months_axis, values


def overspending_flags(
    monthly_income: float,
    monthly_expenses: float,
    category_optional_pct: float = 0.0,
) -> list[str]:
    """Simple overspending detection messages."""
    inc = safe_float(monthly_income)
    exp = safe_float(monthly_expenses)
    out: list[str] = []
    if inc > 0 and exp / inc > 0.95:
        out.append("Expenses consume over 95% of income — review subscriptions and dining out.")
    if exp > inc:
        out.append("Monthly expenses exceed income: use a strict budget or increase income.")
    if category_optional_pct > 35:
        out.append("Discretionary spending is high — try a 24-hour rule for non-essential buys.")
    return out


def financial_tip_generator(profile: UserFinancialProfile) -> list[str]:
    """Rotating practical tips based on profile."""
    tips = [
        "Pay yourself first: set SIP date right after salary credit.",
        "Keep emergency money in sweep FD or liquid funds, not stocks.",
        "Rebalance equity/debt once a year or if allocation drifts >5%.",
    ]
    if safe_float(profile.monthly_investments) < safe_float(profile.monthly_income) * 0.1:
        tips.append("Increase SIP by 10% yearly to match salary increases.")
    if safe_int(profile.age) < 40:
        tips.append("Prioritize term life + health insurance before chasing returns.")
    return tips


def goal_plan(
    goal_type: str,
    target_amount: float,
    years: float,
    expected_return: float = 10.0,
) -> dict[str, Any]:
    """House / car / retirement style goal: required monthly SIP."""
    g = (goal_type or "general").lower()
    ta = safe_float(target_amount)
    y = max(0.5, safe_float(years))
    sip = sip_required_for_target(ta, expected_return, y)
    label = {"house": "Home down payment / goal", "car": "Vehicle goal", "retirement": "Retirement pot"}.get(
        g, "Financial goal"
    )
    return {
        "goal_label": label,
        "target_amount": ta,
        "years": y,
        "monthly_sip_needed": sip,
        "assumed_cagr_pct": expected_return,
    }


def full_retirement_plan(profile: UserFinancialProfile) -> RetirementResult:
    age = safe_int(profile.age)
    ra = safe_int(profile.retirement_age)
    ytr = max(1, ra - age)
    me = safe_float(profile.monthly_expenses)
    inf = 6.0
    annual_exp_retire = me * 12 * ((1 + inf / 100.0) ** ytr)
    corpus = retirement_corpus_needed(me, ytr)
    sip_needed = sip_required_for_target(
        corpus - safe_float(profile.current_savings),
        12.0,
        ytr,
    )
    if corpus < safe_float(profile.current_savings):
        sip_needed = 0.0
    # FIRE number from current annual expenses (4% rule style on today's lifestyle)
    fire_n = fire_number(me * 12)
    ytf = years_to_fire_estimate(
        safe_float(profile.current_savings),
        safe_float(profile.monthly_income),
        safe_float(profile.monthly_expenses),
        fire_corpus=fire_n,
    )
    return RetirementResult(
        years_to_retire=ytr,
        monthly_expense_at_retirement=annual_exp_retire / 12.0,
        corpus_needed=corpus,
        monthly_sip_to_reach=sip_needed,
        fire_number=fire_n,
        years_to_fire=ytf,
    )
