# app.py — AI Money Mentor: hackathon dashboard (fully offline)
"""Tabs: Dashboard, AI Advisor, Goal Planner, Retirement, Wealth Projection, Budget Analyzer."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from budget_engine import budget_vs_actual_insight, generate_budget_table
from charts import (
    fig_health_gauge,
    fig_monthly_breakdown,
    fig_portfolio_growth_scenarios,
    fig_savings_rate_analysis,
    fig_wealth_projection,
    fig_wealth_sip_horizons,
)
from expense_analyzer import analyze_expenses
from financial_calculator import (
    UserFinancialProfile,
    calculate_sip_future_value,
    emergency_fund_recommendation,
    financial_tip_generator,
    full_retirement_plan,
    goal_plan,
    india_tax_saving_suggestions,
    monthly_allocation_breakdown,
    monthly_savings_rate,
)
from financial_score import calculate_money_health
from fire_calculator import compute_fire
from goal_planner import goal_types_for_ui, plan_goal
from offline_ai import explain_strategy_simple, generate_step_by_step_plan, get_offline_advice
from personality import detect_personality
from risk_profile import detect_risk_profile_v2
from utils import format_inr
from wealth_projection import build_projection_pack

# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="AI Money Mentor",
    page_icon="💰",
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
    income_stability = st.sidebar.selectbox(
        "Income stability",
        options=["stable", "somewhat_variable", "variable"],
        format_func=lambda x: {
            "stable": "Stable",
            "somewhat_variable": "Somewhat variable",
            "variable": "Variable / irregular",
        }[x],
    )
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
    st.sidebar.caption("Use **Goal Planner** tab for vacation & custom goals with SIP output.")
    goal_amount = st.sidebar.number_input(
        "Goal amount (₹)", min_value=0.0, value=3_000_000.0, step=100_000.0, format="%.0f"
    )
    goal_years = st.sidebar.number_input("Years to goal", min_value=1, max_value=40, value=12, step=1)

    return UserFinancialProfile(
        age=int(age),
        retirement_age=int(retirement_age),
        monthly_income=float(monthly_income),
        monthly_expenses=float(monthly_expenses),
        current_savings=float(current_savings),
        monthly_investments=float(monthly_investments),
        existing_debt_emi=float(existing_debt_emi),
        income_stability=str(income_stability),
        financial_goal=financial_goal,
        goal_amount=float(goal_amount),
        goal_years=int(goal_years),
    )


def init_chat_state() -> None:
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = [
            {
                "role": "assistant",
                "content": "Hi! I'm your Money Mentor (offline engine). Ask about SIPs, tax, FIRE, emergency funds, or allocation.",
            }
        ]


def _risk_key_for_surplus_alloc(label: str) -> str:
    """Map dashboard risk label to legacy surplus split buckets."""
    m = (label or "").lower()
    if m == "aggressive":
        return "high"
    if m == "conservative":
        return "low"
    return "medium"


def main() -> None:
    init_chat_state()
    profile = get_profile_from_sidebar()

    # --- Core analytics (module-backed) ---------------------------------
    money_health = calculate_money_health(profile)
    risk = detect_risk_profile_v2(profile)
    persona = detect_personality(
        profile.monthly_income,
        profile.monthly_expenses,
        profile.monthly_investments,
    )
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
    sr_pct = monthly_savings_rate(profile.monthly_income, profile.monthly_expenses)
    annual_income = profile.monthly_income * 12
    tax_rows = india_tax_saving_suggestions(annual_income)
    tips = financial_tip_generator(profile)

    # 6× expenses emergency (hackathon spec) vs model recommendation
    ef_required_6mo = profile.monthly_expenses * 6.0
    ef_current = profile.current_savings
    ef_gap_6 = max(0.0, ef_required_6mo - ef_current)

    alloc_breakdown = monthly_allocation_breakdown(
        profile.monthly_income,
        profile.monthly_expenses,
        _risk_key_for_surplus_alloc(risk.label),
    )
    sidebar_goal = goal_plan(
        profile.financial_goal,
        profile.goal_amount,
        float(profile.goal_years),
        10.0,
    )

    st.markdown('<p class="main-header">AI Money Mentor</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="subtle">Advanced offline financial cockpit — Money Health, risk & allocation, FIRE, goals, wealth paths, and smart budgeting. No API keys.</p>',
        unsafe_allow_html=True,
    )

    tab_dash, tab_ai, tab_goal, tab_ret, tab_wealth, tab_budget = st.tabs(
        [
            "Dashboard",
            "AI Advisor",
            "Goal Planner",
            "Retirement Planner",
            "Wealth Projection",
            "Budget Analyzer",
        ]
    )

    # ========================== Dashboard ==========================
    with tab_dash:
        st.subheader("Money Health Score")
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric("Score", f"{money_health.score:.0f}/100", money_health.band)
        with m2:
            st.metric("Savings ratio", f"{money_health.savings_ratio_pct:.1f}%", "of income")
        with m3:
            st.metric("Emergency coverage", f"{money_health.emergency_coverage_pct:.0f}%", "vs 6× target")
        with m4:
            st.metric("Debt (EMI) load", f"{money_health.debt_ratio_pct:.1f}%", "of income")

        st.caption("**Bands:** Excellent (80+) · Good (60–80) · Needs Improvement (below 60)")
        c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(fig_health_gauge(money_health.score), use_container_width=True)
            st.markdown("**Score breakdown (pillars /100)**")
            st.json(money_health.breakdown)

        with c2:
            st.subheader("Risk profile & allocation")
            st.markdown(f"**Risk Profile:** {risk.label}")
            st.markdown(f"_{risk.stability_note}_")
            st.table(
                {
                    "Asset class": ["Equity", "Debt", "Gold"],
                    "Allocation": [
                        f"{risk.allocation.equity_pct}%",
                        f"{risk.allocation.debt_pct}%",
                        f"{risk.allocation.gold_pct}%",
                    ],
                }
            )
            for line in risk.rationale:
                st.caption(f"• {line}")

        st.subheader("Financial personality")
        st.info(f"**{persona.personality}** — {persona.tagline}")
        st.caption(
            f"Savings rate {persona.savings_rate_pct:.1f}% · Expenses {persona.expense_to_income_pct:.1f}% of income · "
            f"Investments {persona.invest_to_income_pct:.1f}% of income"
        )

        st.subheader("Emergency fund planner (6× monthly expenses)")
        e1, e2, e3 = st.columns(3)
        e1.metric("Required", format_inr(ef_required_6mo))
        e2.metric("Current liquid", format_inr(ef_current))
        e3.metric("Gap", format_inr(ef_gap_6))
        st.caption(
            f"Planner model also suggests **{emergency_model.recommended_months} mo** buffer → "
            f"{format_inr(emergency_model.target_amount)} (see Retirement tab for full FIRE)."
        )

        st.subheader("Expense analyzer")
        if expense_report.flags:
            st.warning("**Flags:** " + " · ".join(expense_report.flags))
        for s in expense_report.suggestions:
            st.write("•", s)

        st.subheader("Surplus allocation (from surplus ₹)")
        surplus = max(0.0, profile.monthly_income - profile.monthly_expenses)
        if surplus > 0:
            keys = list(alloc_breakdown.keys())
            st.plotly_chart(
                fig_monthly_breakdown(
                    [k.replace("_", " ").title() for k in keys],
                    list(alloc_breakdown.values()),
                ),
                use_container_width=True,
            )
        else:
            st.info("No surplus to allocate until expenses are below income.")

        st.plotly_chart(
            fig_savings_rate_analysis(
                profile.monthly_income,
                profile.monthly_expenses,
                profile.monthly_investments,
            ),
            use_container_width=True,
        )

        st.plotly_chart(
            fig_portfolio_growth_scenarios(
                profile.current_savings,
                profile.monthly_investments,
                240,
            ),
            use_container_width=True,
        )

        st.subheader("Sidebar goal snapshot")
        st.write(
            f"**{sidebar_goal['goal_label']}** — {format_inr(sidebar_goal['target_amount'])} in "
            f"{sidebar_goal['years']:.0f} yr → ~{format_inr(sidebar_goal['monthly_sip_needed'])}/mo SIP @ "
            f"{sidebar_goal['assumed_cagr_pct']}%"
        )

        st.subheader("AI-style tips (rules)")
        for t in tips:
            st.caption(f"• {t}")

    # ========================== AI Advisor ==========================
    with tab_ai:
        st.subheader("Advisor chat (offline intelligence)")
        st.caption("Responses combine your sidebar profile with rule-based topic engines.")
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
        st.subheader("India tax-saving pointers (education only)")
        for row in tax_rows:
            with st.expander(f"{row['section']} — limit {row['limit']}"):
                st.write(row["ideas"])

        st.subheader("12-month financial plan")
        if st.button("Generate step-by-step plan", key="plan_btn"):
            st.markdown(generate_step_by_step_plan(profile))

        st.subheader("Explain a concept")
        topic = st.text_input("Topic", value="What is SIP and why use it?", key="topic_explain")
        if st.button("Explain in simple words", key="explain_btn"):
            st.markdown(explain_strategy_simple(topic, profile))

    # ========================== Goal Planner ==========================
    with tab_goal:
        st.subheader("Goal-based planner")
        opts = goal_types_for_ui()
        labels = [b for _, b in opts]
        keys = [a for a, _ in opts]
        choice = st.selectbox("Goal type", range(len(opts)), format_func=lambda i: labels[i])
        gkey = keys[choice]
        c1, c2, c3 = st.columns(3)
        with c1:
            target = st.number_input("Target amount (₹)", min_value=0.0, value=1_000_000.0, step=50_000.0, key="g_tgt")
        with c2:
            gyears = st.number_input("Years", min_value=0.5, value=5.0, step=0.5, key="g_yrs")
        with c3:
            gcagr = st.number_input("Assumed CAGR %", min_value=0.0, value=12.0, step=0.5, key="g_rate")

        gp = plan_goal(gkey, target, gyears, gcagr, profile.monthly_investments)
        st.success(
            f"**Goal:** {format_inr(gp.target_amount)} in **{gp.years:g}** years "
            f"({gp.goal_title}) → **Required SIP:** **{format_inr(gp.monthly_sip_required)}**/month"
        )
        fv_line = ""
        if gp.future_value_if_current_sip > 0:
            fv_line = f" At your current **{format_inr(profile.monthly_investments)}/mo** SIP, illustrative FV ≈ **{format_inr(gp.future_value_if_current_sip)}**."
        st.markdown(gp.summary_line + fv_line)

        st.plotly_chart(
            fig_wealth_sip_horizons(
                max(gp.monthly_sip_required, 0.0),
                starting_principal=0.0,
                annual_return=gcagr,
                horizons=(5, 10, 20),
            ),
            use_container_width=True,
        )
        st.caption("Chart uses **required SIP** from zero; returns are illustrative.")

    # ========================== Retirement / FIRE ==========================
    with tab_ret:
        st.subheader("FIRE calculator")
        st.markdown(
            f"- **Required corpus (expenses × 25 × 12):** {format_inr(fire_res.fire_corpus)}\n"
            f"- **Annual expenses (current):** {format_inr(fire_res.annual_expenses)}\n"
        )
        if fire_res.years_to_fire is not None and fire_res.retire_at_age is not None:
            st.success(
                f"You can reach the FIRE corpus in about **{fire_res.years_to_fire:.1f} years** "
                f"— roughly age **{fire_res.retire_at_age:.0f}** (illustrative @ {fire_res.assumed_return_pct}% return)."
            )
        else:
            st.warning(
                "FIRE target not reached in the projection window — raise SIP or lower expenses. "
                f"Illustrative monthly investment to close gap over working years: **{format_inr(fire_res.monthly_investment_needed)}**."
            )
        st.info(fire_res.message)

        ret_col1, ret_col2 = st.columns(2)
        with ret_col1:
            f_age = st.number_input("Max age for bridge-SIP calc", min_value=55, max_value=80, value=65, key="fire_max_age")
        with ret_col2:
            f_ret = st.number_input("Return % for bridge SIP", min_value=4.0, value=10.0, step=0.5, key="fire_ret")
        alt = compute_fire(
            profile.age,
            profile.monthly_income,
            profile.monthly_expenses,
            profile.current_savings,
            profile.monthly_investments,
            max_age=int(f_age),
            assumed_return_pct=float(f_ret),
        )
        st.caption(f"Bridge SIP @ {f_ret}% to corpus by age **{f_age}**: **{format_inr(alt.monthly_investment_needed)}**/month (shortfall vs liquid only).")

        st.divider()
        st.subheader("Traditional retirement model (in app) ")
        st.markdown(
            f"- Years to retirement: **{retirement_legacy.years_to_retire}**\n"
            f"- Monthly need at retirement (illustrative): **{format_inr(retirement_legacy.monthly_expense_at_retirement)}**\n"
            f"- Corpus needed (model): **{format_inr(retirement_legacy.corpus_needed)}**\n"
            f"- Monthly SIP hint: **{format_inr(retirement_legacy.monthly_sip_to_reach)}**\n"
            f"- FIRE number (legacy 4% on expenses): **{format_inr(retirement_legacy.fire_number)}**"
        )

    # ========================== Wealth Projection ==========================
    with tab_wealth:
        st.subheader("Wealth projection (5 / 10 / 20 years)")
        w1, w2 = st.columns(2)
        with w1:
            w_sip = st.number_input("Monthly SIP (₹)", min_value=0.0, value=profile.monthly_investments, step=1000.0, key="w_sip")
        with w2:
            w_lump = st.number_input("Starting principal (₹)", min_value=0.0, value=profile.current_savings, step=50000.0, key="w_p")
        w_rate = st.slider("Annual return % (fixed for chart)", 5.0, 15.0, 12.0, key="w_r")

        pack = build_projection_pack(w_sip, w_lump, w_rate, max_years=20, mark_years=(5, 10, 20))
        st.plotly_chart(
            fig_wealth_sip_horizons(
                monthly_sip=w_sip,
                starting_principal=w_lump,
                annual_return=w_rate,
                horizons=(5, 10, 20),
            ),
            use_container_width=True,
        )
        st.markdown("**Checkpoints**")
        chk_df = pd.DataFrame(
            [{"Horizon (years)": c.years, "Corpus (₹)": c.corpus} for c in pack.checkpoints]
        )
        st.dataframe(chk_df, use_container_width=True, hide_index=True)

        st.plotly_chart(
            fig_wealth_projection(20 * 12, w_lump, w_sip, w_rate),
            use_container_width=True,
        )

    # ========================== Budget Analyzer ==========================
    with tab_budget:
        st.subheader("Smart budget (50% Needs / 30% Wants / 20% Savings)")
        bdf = generate_budget_table(profile.monthly_income)
        st.dataframe(bdf, use_container_width=True, hide_index=True)

        insights = budget_vs_actual_insight(
            profile.monthly_income,
            profile.monthly_expenses,
            profile.monthly_investments,
        )
        st.markdown("**Personalized notes**")
        for ins in insights:
            st.write("•", ins)

        st.subheader("AI-style expense summary")
        if expense_report.flags:
            st.markdown("**Risk flags:** " + ", ".join(expense_report.flags))
        st.markdown(
            f"Expense-to-income **{expense_report.expense_to_income_pct:.1f}%** · "
            f"EMI-to-income **{expense_report.emi_to_income_pct:.1f}%** · "
            f"Savings rate **{expense_report.savings_rate_pct:.1f}%**"
        )
        for s in expense_report.suggestions:
            st.write("•", s)

        st.subheader("Money health & personality (recap)")
        st.metric("Money Health", f"{money_health.score:.0f}/100", money_health.band)
        st.write(f"**{persona.personality}** — {persona.tagline}")


if __name__ == "__main__":
    main()
