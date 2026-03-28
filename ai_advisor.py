# ai_advisor.py — Facade for the offline mentor (no external APIs)
"""Re-exports `offline_ai` so imports stay stable across the app."""

from __future__ import annotations

from financial_calculator import UserFinancialProfile
from offline_ai import (
    explain_strategy_simple,
    generate_step_by_step_plan,
    get_offline_advice,
)
from utils import sanitize_chat_input


def chat_advisor(
    user_message: str,
    profile: UserFinancialProfile,
    history: list[dict[str, str]] | None = None,
) -> tuple[str, str | None]:
    """
    Returns (assistant_reply, error_message).
    Offline engine only — error_message is None on success, or a short hint if input empty.
    `history` is accepted for API compatibility; the offline engine uses the current profile.
    """
    cleaned = sanitize_chat_input(user_message)
    if not cleaned:
        return "", "Please enter a question."
    _ = history  # reserved for future context-aware offline rules
    return get_offline_advice(profile, cleaned), None


def build_context_summary(profile: UserFinancialProfile) -> str:
    """Compact snapshot (for debugging or future extensions)."""
    from financial_calculator import calculate_money_health_score

    health = calculate_money_health_score(profile)
    return (
        f"Age: {profile.age}, retirement age: {profile.retirement_age}. "
        f"Income ₹{profile.monthly_income:,.0f}, expenses ₹{profile.monthly_expenses:,.0f}. "
        f"Savings ₹{profile.current_savings:,.0f}, SIP ₹{profile.monthly_investments:,.0f}, "
        f"EMI ₹{profile.existing_debt_emi:,.0f}. Health: {health.score}/100."
    )
