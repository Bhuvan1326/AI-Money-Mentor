# offline_ai.py — Rule-based “AI” financial mentor (no network, no API)
"""
Personalized advice using profile metrics + keyword intent detection.
All numbers are illustrative; not professional investment or tax advice.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from financial_calculator import (
    UserFinancialProfile,
    calculate_sip_future_value,
    emergency_fund_recommendation,
    full_retirement_plan,
    india_tax_saving_suggestions,
    monthly_savings_rate,
)
from financial_score import calculate_money_health
from risk_profile import detect_risk_profile_v2
from utils import format_inr, sanitize_chat_input


# ---------------------------------------------------------------------------
# Profile snapshot (computed once per response for consistent personalization)
# ---------------------------------------------------------------------------


@dataclass
class ProfileSnapshot:
    age: int
    years_to_retirement: int
    monthly_income: float
    monthly_expenses: float
    savings: float
    sip: float
    emi: float
    surplus: float
    savings_rate_pct: float
    emi_to_income_pct: float
    health_score: float
    health_band: str  # Excellent | Good | Needs Improvement
    risk_label: str  # Conservative | Moderate | Aggressive
    risk_bucket: str  # conservative | moderate | aggressive (logic key)
    equity_pct: int
    debt_pct: int
    gold_pct: int
    emergency_months_target: int
    emergency_gap: float
    retirement_sip_hint: float
    fire_number: float


def _snapshot(profile: UserFinancialProfile) -> ProfileSnapshot:
    income = float(profile.monthly_income)
    exp = float(profile.monthly_expenses)
    surplus = max(0.0, income - exp)
    sr = monthly_savings_rate(income, exp)
    emi = float(profile.existing_debt_emi)
    dti = (emi / income * 100.0) if income > 0 else 0.0
    health = calculate_money_health(profile)
    risk = detect_risk_profile_v2(profile)
    emer = emergency_fund_recommendation(profile)
    ret = full_retirement_plan(profile)
    ytr = max(1, int(profile.retirement_age) - int(profile.age))
    rb = risk.label.lower()

    return ProfileSnapshot(
        age=int(profile.age),
        years_to_retirement=ytr,
        monthly_income=income,
        monthly_expenses=exp,
        savings=float(profile.current_savings),
        sip=float(profile.monthly_investments),
        emi=emi,
        surplus=surplus,
        savings_rate_pct=sr,
        emi_to_income_pct=dti,
        health_score=health.score,
        health_band=health.band,
        risk_label=risk.label,
        risk_bucket=rb,
        equity_pct=risk.allocation.equity_pct,
        debt_pct=risk.allocation.debt_pct,
        gold_pct=risk.allocation.gold_pct,
        emergency_months_target=emer.recommended_months,
        emergency_gap=float(emer.current_gap),
        retirement_sip_hint=float(ret.monthly_sip_to_reach),
        fire_number=float(ret.fire_number),
    )


def _tailored_preamble(s: ProfileSnapshot) -> str:
    """Opening line grounded in the user's numbers."""
    parts: list[str] = []
    parts.append(
        f"Based on your profile (age **{s.age}**, income **{format_inr(s.monthly_income)}/month**, "
        f"expenses **{format_inr(s.monthly_expenses)}**, SIP **{format_inr(s.sip)}**, EMI **{format_inr(s.emi)}**):"
    )
    parts.append(
        f"- **Money health score:** {s.health_score:.0f}/100 — **{s.health_band}**.\n"
        f"- **Savings rate:** {s.savings_rate_pct:.1f}% of income.\n"
        f"- **Risk profile:** **{s.risk_label}** — allocation template **{s.equity_pct}% equity**, **{s.debt_pct}% debt**, **{s.gold_pct}% gold**."
    )
    if s.emi_to_income_pct >= 40:
        parts.append(
            f"- **Debt load:** EMI is about **{s.emi_to_income_pct:.0f}%** of income — prioritize reducing high-cost debt alongside investing."
        )
    elif s.emi_to_income_pct >= 25:
        parts.append(
            f"- **Debt:** EMI is **{s.emi_to_income_pct:.0f}%** of income — keep EMIs predictable before scaling risk."
        )
    if s.savings_rate_pct < 10:
        parts.append(
            "- **Cash flow:** Savings rate is tight — small expense cuts or income steps will unlock more room for goals."
        )
    elif s.savings_rate_pct >= 25:
        parts.append(
            "- **Surplus:** You have a healthy savings rate — you can consider structured equity SIPs within your risk band."
        )
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Intent detection (keyword + light regex)
# ---------------------------------------------------------------------------

_TOPIC_KEYWORDS: dict[str, tuple[str, ...]] = {
    "sip": ("sip", "systematic investment", "monthly investment", "mutual fund sip"),
    "tax": ("tax", "80c", "80d", "nps", "deduction", "itr", "regime", "save tax", "tax saving"),
    "retirement": ("retirement", "retire", "pension", "old age", "corpus"),
    "fire": ("fire", "financial independence", "financially independent", "quit job"),
    "investment": ("invest", "investment", "where to put", "grow money", "returns", "cagr"),
    "emergency": ("emergency", "rainy day", "liquid", "buffer"),
    "mutual_funds": ("mutual fund", "mf", "elss", "index fund", "fund manager", "nav"),
    "portfolio": ("portfolio", "allocation", "asset allocation", "equity debt", "diversify", "rebalance"),
    "savings": ("save money", "budget", "spending", "overspend", "cut expenses", "save more"),
}


def _detect_topics(text: str) -> list[str]:
    t = text.lower().strip()
    if len(t) < 2:
        return []
    found: list[str] = []
    for topic, keys in _TOPIC_KEYWORDS.items():
        if any(k in t for k in keys):
            found.append(topic)
    # De-duplicate preserving order
    seen: set[str] = set()
    out: list[str] = []
    for x in found:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


# ---------------------------------------------------------------------------
# Topic handlers: return markdown sections
# ---------------------------------------------------------------------------


def _section_sip(s: ProfileSnapshot, profile: UserFinancialProfile) -> str:
    fv_10 = calculate_sip_future_value(s.sip, 12.0, 10.0)
    fv_15 = calculate_sip_future_value(s.sip, 12.0, 15.0)
    extra = ""
    if s.surplus > 0 and s.sip < s.surplus * 0.3:
        extra = (
            f"\n\nYour monthly surplus is about **{format_inr(s.surplus)}**. "
            f"Consider stepping SIP toward **{format_inr(min(s.surplus * 0.5, s.sip * 1.2 + 5000))}** "
            f"if emergency fund and high-interest debt are under control."
        )
    if s.age < 40:
        extra += "\n\nAt a younger age, a longer horizon supports **equity-heavy** SIPs (within your risk comfort), not individual stock tips."
    return (
        "### SIP (Systematic Investment Plan)\n\n"
        "**SIP** means investing a fixed amount every month into a mutual fund (or similar). "
        "It builds discipline and **averages purchase cost** over time; returns are **not guaranteed**.\n\n"
        f"At your current **{format_inr(s.sip)}/month** SIP and ~12% illustrative CAGR: "
        f"~**{format_inr(fv_10.future_value, compact=True)}** in 10 years, "
        f"~**{format_inr(fv_15.future_value, compact=True)}** in 15 years (illustrative only)."
        f"{extra}"
    )


def _section_tax(s: ProfileSnapshot, profile: UserFinancialProfile) -> str:
    annual = s.monthly_income * 12
    rows = india_tax_saving_suggestions(annual)
    bullets = "\n".join(
        f"- **{r['section']}** (limit {r['limit']}): {r['ideas']}" for r in rows[:5]
    )
    regime = ""
    if annual > 10_00_000:
        regime = "\n\nWith your income level, **compare old vs new tax regime** using the official income tax calculator before locking ELSS/PPF purely for deduction."
    return (
        "### Tax saving (India — education only)\n\n"
        "Common levers (limits change with law — verify each year):\n\n"
        f"{bullets}"
        f"{regime}\n\n"
        "**Disclaimer:** This is general information, not tax advice; consult a **CA** for your filing."
    )


def _section_retirement(s: ProfileSnapshot, profile: UserFinancialProfile) -> str:
    ret = full_retirement_plan(profile)
    return (
        "### Retirement planning\n\n"
        f"You have about **{ret.years_to_retire}** years to your target retirement age.\n\n"
        f"- **Illustrative corpus needed (model in app):** {format_inr(ret.corpus_needed)}\n"
        f"- **Illustrative monthly SIP to bridge vs current savings @ ~12%:** {format_inr(ret.monthly_sip_to_reach)}\n"
        f"- **Monthly need at retirement (inflation-adjusted, illustrative):** {format_inr(ret.monthly_expense_at_retirement)}\n\n"
        "Increase SIP by a small **percentage yearly** (e.g. 10%) when salary rises; "
        "review **asset mix** as you move closer to retirement."
    )


def _section_fire(s: ProfileSnapshot, profile: UserFinancialProfile) -> str:
    ret = full_retirement_plan(profile)
    ytf = ret.years_to_fire
    line = (
        f"\n\nAt ~10% nominal growth and your current surplus, rough **years to FIRE** ≈ **{ytf:.1f}**."
        if ytf is not None
        else "\n\nFIRE timeline needs a clearer **positive surplus** and realistic return assumption — refine inputs in the app."
    )
    return (
        "### FIRE (Financial Independence)\n\n"
        f"A common shorthand is **~25× annual expenses** invested (4% withdrawal rule — simplified). "
        f"Your **FIRE number** (on current annual expenses) is about **{format_inr(s.fire_number)}**.\n\n"
        "FIRE depends on **spending**, **taxes**, **returns**, and **health costs** — treat this as a planning compass, not a promise."
        f"{line}"
    )


def _section_investment(s: ProfileSnapshot, profile: UserFinancialProfile) -> str:
    if s.risk_bucket == "aggressive" and s.age < 45:
        tilt = "Given your horizon and **higher risk capacity**, a **core equity SIP** plus **debt** for stability can fit—avoid chasing past returns."
    elif s.risk_bucket == "conservative":
        tilt = "Your profile leans **conservative** — favour **debt / hybrid** for short goals and **gradual equity** only for long horizons."
    else:
        tilt = "**Balanced** approach: split long-term money between **equity index/hybrid** and **debt** per goal dates."

    if s.emi_to_income_pct > 35:
        tilt += "\n\n**Priority:** High EMI burden — balance investing with **accelerating costly debt** first."

    return (
        "### Investment approach (general)\n\n"
        f"{tilt}\n\n"
        f"Use **goal buckets** (house, retirement) with different horizons. "
        f"Your template suggests **~{s.equity_pct}% equity** for long-term wealth (funds/indices, not stock tips)."
    )


def _section_emergency(s: ProfileSnapshot, profile: UserFinancialProfile) -> str:
    emer = emergency_fund_recommendation(profile)
    gap_txt = (
        f"You're about **{format_inr(s.emergency_gap)}** short of a **{emer.recommended_months}-month** cushion."
        if s.emergency_gap > 0
        else "You appear **on track or above** the suggested liquid buffer — keep it in **savings / liquid funds**, not volatile assets."
    )
    return (
        "### Emergency fund\n\n"
        f"Target roughly **{emer.recommended_months} months** of expenses (**{format_inr(emer.target_amount)}**) in **liquid**, easy-to-access instruments.\n\n"
        f"{gap_txt}\n\n"
        "Only after this foundation, scale **long-term equity** SIPs aggressively."
    )


def _section_mutual_funds(s: ProfileSnapshot, profile: UserFinancialProfile) -> str:
    return (
        "### Mutual funds (basics)\n\n"
        "**Mutual funds** pool money to buy a basket of stocks/bonds per a stated strategy. "
        "Types you’ll hear in India: **large-cap / flexi-cap / ELSS** (80C), **liquid** for emergency money.\n\n"
        f"For your **{s.risk_label}** profile, focus on **low-cost diversified** funds, **KYC**, and **direct plans** if you self-manage. "
        "Past performance ≠ future results — check **expense ratio**, **portfolio fit**, and **time horizon**."
    )


def _section_portfolio(s: ProfileSnapshot, profile: UserFinancialProfile) -> str:
    return (
        "### Portfolio allocation (rule of thumb)\n\n"
        f"- **Long-term wealth ({s.years_to_retirement}+ yr):** **{s.equity_pct}% equity**, **{s.debt_pct}% debt**, **{s.gold_pct}% gold** (template; rebalance yearly).\n"
        "- **Medium term (3–7 yr):** blend **hybrid / debt-heavy** to reduce drawdown risk.\n"
        "- **Short term (<3 yr):** **FD / liquid / money market** — preserve capital.\n\n"
        "**Rebalance** once a year or if any asset class drifts **~5%** from target."
    )


def _section_savings(s: ProfileSnapshot, profile: UserFinancialProfile) -> str:
    tips: list[str] = []
    if s.savings_rate_pct < 15:
        tips.append(
            "Try a **50/30/20**-style split (needs / wants / save) or track spending for **one month** to find leaks."
        )
    else:
        tips.append("Strong savings discipline — **automate** transfers on salary day so investing happens first.")

    if s.monthly_expenses > s.monthly_income * 0.95:
        tips.append("Expenses are **very close to income** — even small income boosts or subscription audits help.")

    tips.append(
        f"Direct at least **10–15%** of income to **investments** once EMIs and emergency fund are sane; "
        f"you're at **{s.savings_rate_pct:.1f}%** gross savings rate."
    )
    return "### Saving & spending\n\n" + "\n\n".join(f"- {t}" for t in tips)


def _section_general(s: ProfileSnapshot, profile: UserFinancialProfile, question: str) -> str:
    """Fallback: still personalized when no keyword topic matches."""
    ret = full_retirement_plan(profile)
    bridge = format_inr(ret.monthly_sip_to_reach)
    return (
        "### Guidance\n\n"
        f"I didn’t match a specific topic in “{question[:80]}…”, so here’s concise guidance from **your profile**:\n\n"
        f"- **Money health:** {s.health_score:.0f}/100 — keep **emergency liquidity** and **steady SIPs**.\n"
        f"- **Retirement (illustrative):** corpus target ~**{format_inr(ret.corpus_needed)}**; "
        f"monthly SIP to bridge gap ~**{bridge}** at ~12% assumed return.\n"
        f"- **Current SIP:** {format_inr(s.sip)}/month — increase gradually with salary if **debt** and **buffer** allow.\n\n"
        "Try asking about **SIP**, **80C/80D**, **FIRE**, **emergency fund**, **mutual funds**, or **allocation**."
    )


_HANDLERS: dict[str, Callable[[ProfileSnapshot, UserFinancialProfile], str]] = {
    "sip": _section_sip,
    "tax": _section_tax,
    "retirement": _section_retirement,
    "fire": _section_fire,
    "investment": _section_investment,
    "emergency": _section_emergency,
    "mutual_funds": _section_mutual_funds,
    "portfolio": _section_portfolio,
    "savings": _section_savings,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_offline_advice(profile: UserFinancialProfile, question: str) -> str:
    """
    Main entry: personalized, topic-aware markdown answer.
    Uses rules + financial_calculator outputs — no external services.
    """
    cleaned = sanitize_chat_input(question)
    if not cleaned:
        return "Please enter a question so I can tailor guidance to your profile."

    s = _snapshot(profile)
    topics = _detect_topics(cleaned)

    sections: list[str] = [_tailored_preamble(s)]

    if topics:
        for topic in topics[:4]:  # avoid huge replies
            fn = _HANDLERS.get(topic)
            if fn:
                sections.append(fn(s, profile))
    else:
        sections.append(_section_general(s, profile, cleaned))

    sections.append(
        "\n---\n*Figures are illustrative. Not investment, tax, or legal advice.*"
    )
    return "\n\n".join(sections)


def generate_step_by_step_plan(profile: UserFinancialProfile) -> str:
    """12-month plan: dynamic steps from savings ratio, EMI, emergency gap, risk."""
    s = _snapshot(profile)
    emer = emergency_fund_recommendation(profile)
    steps: list[str] = []

    if s.emergency_gap > 0:
        steps.append(
            f"**Months 1–3 — Emergency fund:** Move **{format_inr(min(s.emergency_gap / 3, s.surplus))}**/month (if possible) "
            f"into liquid savings until you reach **{emer.recommended_months} months** of expenses (**{format_inr(emer.target_amount)}**)."
        )
    else:
        steps.append(
            "**Months 1–3 — Maintain buffer:** Keep **6+ months** expenses in liquid instruments; avoid chasing equity with this bucket."
        )

    if s.emi_to_income_pct > 40:
        steps.append(
            "**Debt focus:** List loans by **interest rate**; prepay **costliest** (often credit card / personal) before increasing risk assets."
        )

    if s.savings_rate_pct < 15:
        steps.append(
            "**Budget sprint:** Track every expense for **30 days**; cap discretionary categories by **10–15%** to fund SIPs."
        )

    if s.age < 40 and s.risk_bucket in ("moderate", "aggressive"):
        steps.append(
            f"**SIP automation:** Set **{format_inr(max(s.sip, s.surplus * 0.25))}**/month equity SIP (illustrative) on salary date — "
            "increase **10% yearly** with raises."
        )
    else:
        steps.append(
            f"**Invest steadily:** Target **{format_inr(s.sip)}**/month into diversified funds aligned to **{s.risk_label}** risk, "
            "with debt allocation for nearer goals."
        )

    steps.append(
        "**Tax (India):** Use **80C** (ELSS/PPF/EPF), **80D** (health), optional **NPS 80CCD(1B)** — compare **old vs new** regime."
    )
    steps.append(
        "**Insurance:** Term life if dependents; **health cover** ≥ reasonable sum insured for your city/hospital costs."
    )
    steps.append(
        "**Quarterly review:** Revisit **SIP amount**, **EMI prepayments**, and **allocation**; rebalance yearly."
    )

    numbered = "\n".join(f"{i + 1}. {txt}" for i, txt in enumerate(steps[:10]))
    return f"### Your 12-month roadmap\n\n{numbered}\n\n---\n*Educational only — not personalized professional advice.*"


def explain_strategy_simple(topic: str, profile: UserFinancialProfile) -> str:
    """Longer explanation for a free-text topic; reuses same engine + extra prose."""
    cleaned = sanitize_chat_input(topic, max_len=2000)
    if not cleaned:
        return "Enter a topic (e.g. SIP, ELSS, FIRE)."
    s = _snapshot(profile)
    base = get_offline_advice(profile, cleaned)
    # Add a short “how this applies to you” closing
    closing = (
        f"\n\n### Your takeaway\n\n"
        f"With a **{s.savings_rate_pct:.1f}%** savings rate and **{s.risk_label}** risk band, "
        f"prioritize **liquidity → high-cost debt → tax-efficient SIPs** in that order where applicable."
    )
    return base + closing
