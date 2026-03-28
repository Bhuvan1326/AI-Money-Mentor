"""Uses combined household SIP math; fully offline."""

from __future__ import annotations

from dataclasses import dataclass

from financial_calculator import sip_required_for_target


@dataclass
class JointMilestone:
    name: str
    description: str
    target_amount_inr: float
    years: float
    assumed_cagr_pct: float
    monthly_sip_required: float


DEFAULT_HOUSE_INR = 8_000_000.0
DEFAULT_EDU_INR = 2_500_000.0
DEFAULT_RET_CORPUS_INR = 15_000_000.0


def plan_joint_milestones(
    house_target: float,
    house_years: float,
    edu_target: float,
    edu_years: float,
    retirement_corpus_target: float,
    retirement_years: float,
    cagr: float = 12.0,
) -> list[JointMilestone]:
    """Three parallel goals — SIP computed independently per goal (conservative upper bound)."""
    cagr = float(cagr)
    out: list[JointMilestone] = []

    out.append(
        JointMilestone(
            name="House purchase",
            description="Down payment / purchase corpus goal",
            target_amount_inr=float(house_target),
            years=float(house_years),
            assumed_cagr_pct=cagr,
            monthly_sip_required=sip_required_for_target(house_target, cagr, house_years),
        )
    )
    out.append(
        JointMilestone(
            name="Child education",
            description="Education fund (lumpsum target)",
            target_amount_inr=float(edu_target),
            years=float(edu_years),
            assumed_cagr_pct=cagr,
            monthly_sip_required=sip_required_for_target(edu_target, cagr, edu_years),
        )
    )
    out.append(
        JointMilestone(
            name="Retirement corpus",
            description="Additional retirement pot on top of existing savings trajectory",
            target_amount_inr=float(retirement_corpus_target),
            years=float(retirement_years),
            assumed_cagr_pct=cagr,
            monthly_sip_required=sip_required_for_target(retirement_corpus_target, cagr, retirement_years),
        )
    )
    return out


def total_parallel_sip_pressure(milestones: list[JointMilestone]) -> float:
    """Sum of required SIPs if goals are fully funded in parallel (upper bound)."""
    return float(sum(m.monthly_sip_required for m in milestones))
