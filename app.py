"""Couple Mode aggregates Partner A + B; all engines consume one combined UserFinancialProfile."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from budget_engine import budget_vs_actual_insight, generate_budget_table
from charts import (
    fig_health_gauge,
    fig_income_share_pie,
    fig_monthly_breakdown,
    fig_portfolio_growth_scenarios,
    fig_savings_rate_analysis,
    fig_wealth_projection,
    fig_wealth_sip_horizons,
)
from couple_mode import CoupleAdviceBundle, build_couple_bundle
from couple_planner import (
    DEFAULT_EDU_INR,
    DEFAULT_HOUSE_INR,
    DEFAULT_RET_CORPUS_INR,
    plan_joint_milestones,
    total_parallel_sip_pressure,
)
from expense_analyzer import analyze_expenses
from financial_calculator import (
    UserFinancialProfile,
    emergency_fund_recommendation,
    financial_tip_generator,
    full_retirement_plan,
    goal_plan,
    india_tax_saving_suggestions,
    monthly_allocation_breakdown,
)
from financial_score import calculate_money_health
from fire_calculator import compute_fire
from goal_planner import goal_types_for_ui, plan_goal
from joint_calculator import PartnerInputs, build_couple_user_profile
from offline_ai import explain_strategy_simple, generate_step_by_step_plan, get_offline_advice
from personality import detect_personality
from risk_profile import RiskProfileOutcome, detect_risk_profile_v2
from utils import format_inr
from wealth_projection import build_projection_pack

# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="SmartWealth AI",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)

FIN_CSS = """
<style>
    .main-header { font-size: 1.75rem; font-weight: 700; color: #0f172a; letter-spacing: -0.02em; }
    .subtle { color: #64748b; font-size: 0.95rem; }
    div[data-testid="stSidebar"] { background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%); }
    div[data-testid="stSidebar"] * { color: #e2e8f0 !important; }
    div[data-testid="stSidebar"] label { color: #cbd5e1 !important; }
    .stChatMessage { background: #f8fafc; border-radius: 8px; }
</style>
"""
st.markdown(FIN_CSS, unsafe_allow_html=True)


def get_profile_from_sidebar() -> UserFinancialProfile:
    st.sidebar.markdown("### Your profile")
    age = st.sidebar.number_input("Age", min_value=18, max_value=100, value=32, step=1)
    retirement_age = st.sidebar.number_input(
        "Target retirement age", min_value=40, max_value=80, value=58, step=1
    )
    monthly_income = st.sidebar.number_input(
        "Monthly income (₹)", min_value=0.0, value=120_000.0, step=1000.0, format="%.0f"
    )
    monthly_expenses = st.sidebar.number_input(
        "Monthly expenses (₹)", min_value=0.0, value=70_000.0, step=1000.0, format="%.0f"
    )
    current_savings = st.sidebar.number_input(
        "Current savings / liquid corpus (₹)", min_value=0.0, value=800_000.0, step=50_000.0, format="%.0f"
    )
    monthly_investments = st.sidebar.number_input(
        "Monthly SIP / investments (₹)", min_value=0.0, value=18_000.0, step=1000.0, format="%.0f"
    )
    existing_debt_emi = st.sidebar.number_input(
        "Total EMI (loans) per month (₹)", min_value=0.0, value=12_000.0, step=500.0, format="%.0f"
    )
    income_stability = _sidebar_stability()
    fin_goal, g_amt, g_yrs = _sidebar_goal_block()
    return UserFinancialProfile(
        age=int(age),
        retirement_age=int(retirement_age),
        monthly_income=float(monthly_income),
        monthly_expenses=float(monthly_expenses),
        current_savings=float(current_savings),
        monthly_investments=float(monthly_investments),
        existing_debt_emi=float(existing_debt_emi),
        income_stability=income_stability,
        financial_goal=fin_goal,
        goal_amount=float(g_amt),
        goal_years=int(g_yrs),
    )


def _sidebar_stability() -> str:
    return st.sidebar.selectbox(
        "Income stability",
        options=["stable", "somewhat_variable", "variable"],
        format_func=lambda x: {
            "stable": "Stable",
            "somewhat_variable": "Somewhat variable",
            "variable": "Variable / irregular",
        }[x],
    )


def _sidebar_goal_block() -> tuple[str, float, int]:
    st.sidebar.markdown("### Quick goal (sidebar)")
    financial_goal = st.sidebar.selectbox(
        "Primary goal",
        options=["retirement", "house", "car", "emergency"],
        format_func=lambda x: {
            "retirement": "Retirement",
            "house": "House",
            "car": "Car",
            "emergency": "Emergency fund",
        }[x],
    )
    goal_amount = st.sidebar.number_input(
        "Goal amount (₹)", min_value=0.0, value=3_000_000.0, step=100_000.0, format="%.0f"
    )
    goal_years = st.sidebar.number_input("Years to goal", min_value=1, max_value=40, value=12, step=1)
    return financial_goal, goal_amount, goal_years


def get_couple_from_sidebar() -> tuple[UserFinancialProfile, CoupleAdviceBundle]:
    st.sidebar.markdown("### Couple mode — Partner A")
    aa = st.sidebar.number_input("A: Age", 18, 100, 32, 1, key="ca_age")
    ara = st.sidebar.number_input("A: Target retirement age", 40, 80, 58, 1, key="ca_ret")
    ia = st.sidebar.number_input("A: Monthly income (₹)", 0.0, value=80_000.0, step=1000.0, format="%.0f", key="ca_inc")
    ea = st.sidebar.number_input("A: Monthly expenses (₹)", 0.0, value=35_000.0, step=1000.0, format="%.0f", key="ca_exp")
    sa = st.sidebar.number_input("A: Liquid savings (₹)", 0.0, value=400_000.0, step=25000.0, format="%.0f", key="ca_sav")
    sipa = st.sidebar.number_input("A: Monthly SIP (₹)", 0.0, value=10_000.0, step=500.0, format="%.0f", key="ca_sip")
    emia = st.sidebar.number_input("A: EMI (₹)", 0.0, value=8_000.0, step=500.0, format="%.0f", key="ca_emi")

    st.sidebar.markdown("### Partner B")
    ab = st.sidebar.number_input("B: Age", 18, 100, 34, 1, key="cb_age")
    arb = st.sidebar.number_input("B: Target retirement age", 40, 80, 60, 1, key="cb_ret")
    ib = st.sidebar.number_input("B: Monthly income (₹)", 0.0, value=70_000.0, step=1000.0, format="%.0f", key="cb_inc")
    eb = st.sidebar.number_input("B: Monthly expenses (₹)", 0.0, value=32_000.0, step=1000.0, format="%.0f", key="cb_exp")
    sb = st.sidebar.number_input("B: Liquid savings (₹)", 0.0, value=450_000.0, step=25000.0, format="%.0f", key="cb_sav")
    sipb = st.sidebar.number_input("B: Monthly SIP (₹)", 0.0, value=9_000.0, step=500.0, format="%.0f", key="cb_sip")
    emib = st.sidebar.number_input("B: EMI (₹)", 0.0, value=6_000.0, step=500.0, format="%.0f", key="cb_emi")

    st.sidebar.markdown("### Household (shared)")
    stability = _sidebar_stability()
    fin_goal, g_amt, g_yrs = _sidebar_goal_block()

    pa = PartnerInputs(
        int(aa),
        int(ara),
        float(ia),
        float(ea),
        float(sa),
        float(sipa),
        float(emia),
    )
    pb = PartnerInputs(
        int(ab),
        int(arb),
        float(ib),
        float(eb),
        float(sb),
        float(sipb),
        float(emib),
    )
    prof, _meta = build_couple_user_profile(pa, pb, income_stability=stability, financial_goal=fin_goal, goal_amount=g_amt, goal_years=g_yrs)
    bundle = build_couple_bundle(_meta, prof)
    return prof, bundle


def init_chat_state() -> None:
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = [
            {
                "role": "assistant",
                "content": "Hi! I'm your Money Mentor. Toggle **Couple Mode** for joint household planning.",
            }
        ]


def _risk_key_for_surplus_alloc(label: str) -> str:
    m = (label or "").lower()
    if m == "aggressive":
        return "high"
    if m == "conservative":
        return "low"
    return "medium"


def _run_core_analytics(
    profile: UserFinancialProfile,
    risk: RiskProfileOutcome,
    couple_on: bool,
):
    """Recompute all shared metrics (combined profile when couple)."""
    money_health = calculate_money_health(profile, context="couple" if couple_on else "single")
    persona = detect_personality(profile.monthly_income, profile.monthly_expenses, profile.monthly_investments)
    expense_report = analyze_expenses(
        profile.monthly_income,
        profile.monthly_expenses,
        profile.existing_debt_emi,
        profile.monthly_investments,
    )
    fire_res = compute_fire(
        profile.age,
        profile.monthly_income,
        profile.monthly_expenses,
        profile.current_savings,
        profile.monthly_investments,
    )
    retirement_legacy = full_retirement_plan(profile)
    emergency_model = emergency_fund_recommendation(profile)
    annual_income = profile.monthly_income * 12
    tax_rows = india_tax_saving_suggestions(annual_income)
    tips = financial_tip_generator(profile)
    ef_required_6mo = profile.monthly_expenses * 6.0
    ef_gap_6 = max(0.0, ef_required_6mo - profile.current_savings)
    alloc_breakdown = monthly_allocation_breakdown(
        profile.monthly_income,
        profile.monthly_expenses,
        _risk_key_for_surplus_alloc(risk.label),
    )
    sidebar_goal = goal_plan(profile.financial_goal, profile.goal_amount, float(profile.goal_years), 10.0)
    return {
        "money_health": money_health,
        "risk": risk,
        "persona": persona,
        "expense_report": expense_report,
        "fire_res": fire_res,
        "retirement_legacy": retirement_legacy,
        "emergency_model": emergency_model,
        "tax_rows": tax_rows,
        "tips": tips,
        "ef_required_6mo": ef_required_6mo,
        "ef_gap_6": ef_gap_6,
        "alloc_breakdown": alloc_breakdown,
        "sidebar_goal": sidebar_goal,
    }


def _dashboard_body(z: dict, profile: UserFinancialProfile, couple_on: bool, bundle: CoupleAdviceBundle | None):
    mh, risk = z["money_health"], z["risk"]
    st.subheader("Couple Money Health Score" if couple_on else "Money Health Score")
    m1, m2, m3, m4 = st.columns(4)
    score_label = "Couple score" if couple_on else "Score"
    with m1:
        st.metric(score_label, f"{mh.score:.0f}/100", mh.band)
    with m2:
        st.metric("Savings ratio", f"{mh.savings_ratio_pct:.1f}%", "of income")
    with m3:
        st.metric("Emergency vs 6×", f"{mh.emergency_coverage_pct:.0f}%", "coverage")
    with m4:
        st.metric("EMI load", f"{mh.debt_ratio_pct:.1f}%", "of income")
    st.caption("Bands: Excellent (80+) · Good (60–80) · Needs improvement (below 60)")

    if couple_on and bundle is not None:
        st.info(
            f"**Household:** {format_inr(bundle.meta.total_income)}/mo in · "
            f"{format_inr(bundle.meta.total_expenses)}/mo out · "
            f"net **{format_inr(bundle.meta.monthly_surplus_flow)}/mo** · "
            f"first retirement **~{bundle.meta.years_to_first_retirement}** yrs (Partner **{bundle.meta.first_retirer}**)."
        )
        st.plotly_chart(
            fig_income_share_pie(
                "Partner A",
                bundle.meta.partner_a_income,
                bundle.meta.partner_b_income
            ),
            use_container_width=True,
            key="income_share_dashboard"
        )

    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(
            fig_health_gauge(mh.score),
            use_container_width=True,
            key="health_gauge_chart"
        )
        st.json(mh.breakdown)
    with c2:
        st.subheader("Risk & allocation")
        st.markdown(f"**Risk profile:** {risk.label}")
        if couple_on:
            st.caption("Couple heuristic: ages + joint EMI vs income.")
        st.markdown(f"_{risk.stability_note}_")
        st.dataframe(
            pd.DataFrame(
                {
                    "Asset class": ["Equity", "Debt", "Gold"],
                    "Allocation": [f"{risk.allocation.equity_pct}%", f"{risk.allocation.debt_pct}%", f"{risk.allocation.gold_pct}%"],
                }
            ),
            use_container_width=True,
            hide_index=True,
        )
        for line in risk.rationale:
            st.caption(f"• {line}")

    st.subheader("Financial personality (household)")
    st.info(f"**{z['persona'].personality}** — {z['persona'].tagline}")

    st.subheader("Emergency fund (6× monthly household expenses)")
    e1, e2, e3 = st.columns(3)
    e1.metric("Required", format_inr(z["ef_required_6mo"]))
    e2.metric("Current liquid", format_inr(profile.current_savings))
    e3.metric("Gap", format_inr(z["ef_gap_6"]))

    st.subheader("Expense analyzer")
    er = z["expense_report"]
    if er.flags:
        st.warning("**Flags:** " + " · ".join(er.flags))
    for s in er.suggestions:
        st.write("•", s)

    surplus = max(0.0, profile.monthly_income - profile.monthly_expenses)
    if surplus > 0:
        ab = z["alloc_breakdown"]
        st.plotly_chart(
            fig_monthly_breakdown(
                [k.replace("_", " ").title() for k in ab],
                list(ab.values()),
            ),
            use_container_width=True,
            key="monthly_breakdown_chart"
        )
    st.plotly_chart(
        fig_savings_rate_analysis(
            profile.monthly_income,
            profile.monthly_expenses,
            profile.monthly_investments
        ),
        use_container_width=True,
        key="savings_rate_chart"
    )
    st.plotly_chart(
        fig_portfolio_growth_scenarios(
            profile.current_savings,
            profile.monthly_investments,
            240
        ),
        use_container_width=True,
        key="portfolio_growth_chart"
    )
    sg = z["sidebar_goal"]
    st.subheader("Sidebar goal snapshot")
    st.write(
        f"**{sg['goal_label']}** — {format_inr(sg['target_amount'])} in {sg['years']:.0f} yr → "
        f"~{format_inr(sg['monthly_sip_needed'])}/mo SIP @ {sg['assumed_cagr_pct']}%"
    )
    for t in z["tips"]:
        st.caption(f"• {t}")

    if couple_on and bundle is not None:
        st.subheader("Couple advisory snippets")
        for line in bundle.advice_lines:
            st.write("•", line)


def main() -> None:
    init_chat_state()
    st.markdown('<p class="main-header">SmartWealth AI</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="subtle">Planning — single or couple / joint household mode.</p>',
        unsafe_allow_html=True,
    )
    couple_on = st.toggle("Enable Couple Mode", value=False, help="Combine Partner A + B inputs across all calculators.")

    if couple_on:
        profile, couple_bundle = get_couple_from_sidebar()
        risk = couple_bundle.risk
    else:
        profile = get_profile_from_sidebar()
        couple_bundle = None
        risk = detect_risk_profile_v2(profile)

    z = _run_core_analytics(profile, risk, couple_on)

    if couple_on:
        cd, jp, cb, rp, ai = st.tabs(
            ["Couple Dashboard", "Joint Planning", "Combined Budget", "Retirement Planning", "AI Advisor"]
        )

        with cd:
            _dashboard_body(z, profile, True, couple_bundle)

        with jp:
            st.subheader("Joint milestone planner")
            st.caption("Independent SIP math per goal — sum is an upper bound if all run in parallel.")
            j1, j2, j3 = st.columns(3)
            with j1:
                ht = st.number_input("House target (₹)", 0.0, value=DEFAULT_HOUSE_INR, step=100_000.0, key="jh")
                hy = st.number_input("House years", 0.5, value=10.0, step=0.5, key="jhy")
            with j2:
                et = st.number_input("Education target (₹)", 0.0, value=DEFAULT_EDU_INR, step=50_000.0, key="je")
                ey = st.number_input("Education years", 0.5, value=15.0, step=0.5, key="jey")
            with j3:
                rt = st.number_input("Retirement corpus add-on (₹)", 0.0, value=DEFAULT_RET_CORPUS_INR, step=500_000.0, key="jr")
                ry = st.number_input("Retirement years", 0.5, value=20.0, step=0.5, key="jry")
            jcagr = st.slider("Assumed CAGR % (all three)", 6.0, 15.0, 12.0, key="jcagr")
            miles = plan_joint_milestones(ht, hy, et, ey, rt, ry, jcagr)
            total = total_parallel_sip_pressure(miles)
            for m in miles:
                st.success(
                    f"**{m.name}** — {format_inr(m.target_amount_inr)} in **{m.years:g}** yrs → "
                    f"**{format_inr(m.monthly_sip_required)}**/mo"
                )
            st.warning(f"**Parallel SIP sum (illustrative ceiling):** {format_inr(total)}/month")
            st.plotly_chart(
                fig_wealth_sip_horizons(
                    profile.monthly_investments,
                    profile.current_savings,
                    jcagr,
                    (5, 10, 20)
                ),
                use_container_width=True,
                key="joint_planner_chart"
            )

        with cb:
            st.subheader("Joint budget — 50 / 30 / 20 on combined income")
            st.dataframe(generate_budget_table(profile.monthly_income), use_container_width=True, hide_index=True)
            for ins in budget_vs_actual_insight(
                profile.monthly_income, profile.monthly_expenses, profile.monthly_investments
            ):
                st.write("•", ins)
            if couple_bundle:
                st.plotly_chart(
                 fig_income_share_pie(
                  "Partner A",
                  couple_bundle.meta.partner_a_income,
                  couple_bundle.meta.partner_b_income
                 ),
                 use_container_width=True,
                 key="budget_income_share"
                )

        with rp:
            st.subheader("Couple retirement & FIRE")
            st.markdown(
                f"- **Household FIRE corpus (expenses × 25 × 12):** {format_inr(z['fire_res'].fire_corpus)}\n"
                f"- **Avg planning age in profile:** {profile.age} · **Retirement age field:** {profile.retirement_age}\n"
            )
            if couple_bundle:
                st.info(
                    f"**Earliest retirement path:** ~**{couple_bundle.meta.years_to_first_retirement}** years "
                    f"(Partner **{couple_bundle.meta.first_retirer}** reaches their target age first — illustrative)."
                )
            fr = z["fire_res"]
            if fr.years_to_fire is not None and fr.retire_at_age is not None:
                st.success(
                    f"FIRE corpus in ~**{fr.years_to_fire:.1f}** yrs (age ~**{fr.retire_at_age:.0f}**, @ {fr.assumed_return_pct}%)."
                )
            else:
                st.warning(f"Stretch target — consider raising joint SIP toward **{format_inr(fr.monthly_investment_needed)}**/mo.")
            st.info(fr.message)
            st.divider()
            st.markdown("### Legacy retirement model (combined inputs)")
            rl = z["retirement_legacy"]
            st.markdown(
                f"- Years to retirement (avg-age profile): **{rl.years_to_retire}**\n"
                f"- Corpus (model): **{format_inr(rl.corpus_needed)}**\n"
                f"- SIP hint: **{format_inr(rl.monthly_sip_to_reach)}**"
            )

        with ai:
            st.caption("Joint context enabled — answers reference combined household.")
            for msg in st.session_state.chat_messages:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
            user_q = st.chat_input("Ask about your joint finances...")
            if user_q:
                st.session_state.chat_messages.append({"role": "user", "content": user_q})
                st.session_state.chat_messages.append(
                    {"role": "assistant", "content": get_offline_advice(profile, question=user_q, couple_bundle=couple_bundle)}
                )
                st.rerun()
            st.divider()
            for row in z["tax_rows"]:
                with st.expander(f"{row['section']} — {row['limit']}"):
                    st.write(row["ideas"])
            if st.button("12-month joint plan", key="cplan"):
                st.markdown(generate_step_by_step_plan(profile, couple_bundle=couple_bundle))
            top = st.text_input("Explain topic", value="How should couples split SIPs?", key="cex")
            if st.button("Explain", key="cebtn"):
                st.markdown(explain_strategy_simple(top, profile, couple_bundle=couple_bundle))

    else:
        td, tai, tg, tr, tw, tb = st.tabs(
            ["Dashboard", "AI Advisor", "Goal Planner", "Retirement Planner", "Wealth Projection", "Budget Analyzer"]
        )

        with td:
            _dashboard_body(z, profile, False, None)

        with tai:
            for msg in st.session_state.chat_messages:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
            user_q = st.chat_input("Ask your Money Mentor...")
            if user_q:
                st.session_state.chat_messages.append({"role": "user", "content": user_q})
                st.session_state.chat_messages.append(
                    {"role": "assistant", "content": get_offline_advice(profile, user_q)}
                )
                st.rerun()
            st.divider()
            for row in z["tax_rows"]:
                with st.expander(f"{row['section']} — {row['limit']}"):
                    st.write(row["ideas"])
            if st.button("Generate step-by-step plan", key="plan_btn"):
                st.markdown(generate_step_by_step_plan(profile))
            topic = st.text_input("Topic", value="What is SIP and why use it?", key="topic_explain")
            if st.button("Explain in simple words", key="explain_btn"):
                st.markdown(explain_strategy_simple(topic, profile))

        with tg:
            opts = goal_types_for_ui()
            labels = [b for _, b in opts]
            keys = [a for a, _ in opts]
            choice = st.selectbox("Goal type", range(len(opts)), format_func=lambda i: labels[i])
            gkey = keys[choice]
            c1, c2, c3 = st.columns(3)
            with c1:
                target = st.number_input("Target (₹)", min_value=0.0, value=1_000_000.0, step=50_000.0, key="g_tgt")
            with c2:
                gyears = st.number_input("Years", min_value=0.5, value=5.0, step=0.5, key="g_yrs")
            with c3:
                gcagr = st.number_input("CAGR %", min_value=0.0, value=12.0, step=0.5, key="g_rate")
            gp = plan_goal(gkey, target, gyears, gcagr, profile.monthly_investments)
            st.success(
                f"**Goal:** {format_inr(gp.target_amount)} in **{gp.years:g}** yr ({gp.goal_title}) → "
                f"**{format_inr(gp.monthly_sip_required)}**/mo"
            )
            st.plotly_chart(
                    fig_wealth_sip_horizons(
                     max(gp.monthly_sip_required, 0.0),
                     0.0,
                     gcagr,
                     (5, 10, 20)
                    ),
                    use_container_width=True,
                    key="goal_planner_chart"
            )
        with tr:
            fr = z["fire_res"]
            st.markdown(
                f"- **FIRE corpus:** {format_inr(fr.fire_corpus)}\n"
                f"- **Annual expenses:** {format_inr(fr.annual_expenses)}\n"
            )
            if fr.years_to_fire is not None:
                st.success(f"~**{fr.years_to_fire:.1f}** yrs to FIRE (age ~**{fr.retire_at_age:.0f}**).")
            else:
                st.warning(f"Bridge SIP idea: **{format_inr(fr.monthly_investment_needed)}**/mo")
            st.info(fr.message)
            rl = z["retirement_legacy"]
            st.markdown(
                f"**Traditional model:** {rl.years_to_retire} yrs · corpus **{format_inr(rl.corpus_needed)}** · "
                f"SIP **{format_inr(rl.monthly_sip_to_reach)}**"
            )

        with tw:
            w_sip = st.number_input("Monthly SIP (₹)", min_value=0.0, value=profile.monthly_investments, step=1000.0, key="w_sip")
            w_lump = st.number_input("Principal (₹)", min_value=0.0, value=profile.current_savings, step=50000.0, key="w_p")
            w_rate = st.slider("Return %", 5.0, 15.0, 12.0, key="w_r")
            pack = build_projection_pack(w_sip, w_lump, w_rate, max_years=20, mark_years=(5, 10, 20))
            st.plotly_chart(
                fig_wealth_sip_horizons(
                    w_sip,
                    w_lump,
                    w_rate,
                    (5, 10, 20)
                ),
                use_container_width=True,
                key="wealth_horizon_chart"
            )            
            st.dataframe(
                pd.DataFrame([{"Horizon (years)": c.years, "Corpus (₹)": c.corpus} for c in pack.checkpoints]),
                use_container_width=True,
                hide_index=True,
            )
        st.plotly_chart(
            fig_wealth_projection(
                20 * 12,
                w_lump,
                w_sip,
                w_rate
            ),
            use_container_width=True,
            key="wealth_projection_chart"
        )
        with tb:
            st.dataframe(generate_budget_table(profile.monthly_income), use_container_width=True, hide_index=True)
            for ins in budget_vs_actual_insight(profile.monthly_income, profile.monthly_expenses, profile.monthly_investments):
                st.write("•", ins)
            er = z["expense_report"]
            if er.flags:
                st.markdown("**Flags:** " + ", ".join(er.flags))
            st.metric("Money Health", f"{z['money_health'].score:.0f}/100", z["money_health"].band)


if __name__ == "__main__":
    main()
