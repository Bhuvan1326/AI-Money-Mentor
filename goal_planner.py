# goal_planner.py — Goal-based SIP and future value (offline)
"""Buy house / car / vacation / retirement / custom goal."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from financial_calculator import calculate_sip_future_value, sip_required_for_target


class GoalType(str, Enum):
    BUY_HOUSE = "buy_house"
    BUY_CAR = "buy_car"
    RETIREMENT = "retirement"
    VACATION = "vacation"
    CUSTOM = "custom"


GOAL_LABELS: dict[str, str] = {
    GoalType.BUY_HOUSE.value: "Buy House",
    GoalType.BUY_CAR.value: "Buy Car",
    GoalType.RETIREMENT.value: "Retirement",
    GoalType.VACATION.value: "Vacation",
    GoalType.CUSTOM.value: "Custom Goal",
}


@dataclass
class GoalPlanResult:
    goal_key: str
    goal_title: str
    target_amount: float
    years: float
    assumed_cagr_pct: float
    monthly_sip_required: float
    future_value_if_current_sip: float  # illustrative if user keeps a reference SIP
    summary_line: str


def plan_goal(
    goal_key: str,
    target_amount: float,
    years: float,
    assumed_cagr_pct: float = 12.0,
    reference_monthly_sip: float = 0.0,
) -> GoalPlanResult:
    """
    Compute required monthly SIP for target_amount in `years` at assumed_cagr_pct.
    Optionally show FV if investing reference_monthly_sip for same horizon.
    """
    key = (goal_key or GoalType.CUSTOM.value).lower().strip()
    if key not in GOAL_LABELS:
        key = GoalType.CUSTOM.value
    title = GOAL_LABELS.get(key, "Custom Goal")

    tgt = max(0.0, float(target_amount))
    y = max(0.5, float(years))
    rate = float(assumed_cagr_pct)

    sip_need = sip_required_for_target(tgt, rate, y)
    ref = max(0.0, float(reference_monthly_sip))
    fv_ref = calculate_sip_future_value(ref, rate, y).future_value if ref > 0 else 0.0

    summary = (
        f"Goal: **{title}** — {tgt:,.0f} INR in {y:.1f} years @ ~{rate}% CAGR → "
        f"**{sip_need:,.0f} INR/month** SIP required (illustrative)."
    )
    return GoalPlanResult(
        goal_key=key,
        goal_title=(
            title
            if key != GoalType.CUSTOM.value
            else f"Custom Goal: {tgt:,.0f} INR"
        ),
        target_amount=tgt,
        years=y,
        assumed_cagr_pct=rate,
        monthly_sip_required=float(sip_need),
        future_value_if_current_sip=float(fv_ref),
        summary_line=summary,
    )


def goal_types_for_ui() -> list[tuple[str, str]]:
    """(value, display) pairs for Streamlit selectbox — stable display order."""
    order = [
        GoalType.BUY_HOUSE.value,
        GoalType.BUY_CAR.value,
        GoalType.RETIREMENT.value,
        GoalType.VACATION.value,
        GoalType.CUSTOM.value,
    ]
    return [(k, GOAL_LABELS[k]) for k in order]
