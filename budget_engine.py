# budget_engine.py — 50 / 30 / 20 smart budget (personalized to income)
"""Needs 50%, Wants 30%, Savings 20% of net monthly income."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from utils import safe_float


@dataclass
class BudgetRule:
    needs_pct: float = 50.0
    wants_pct: float = 30.0
    savings_pct: float = 20.0


def generate_budget_table(monthly_income: float, rule: BudgetRule | None = None) -> pd.DataFrame:
    """
    Returns a table with category, %, and INR amount.
    If income is 0, returns zero rows with structure preserved.
    """
    r = rule or BudgetRule()
    inc = max(0.0, safe_float(monthly_income))
    data = [
        {"Category": "Needs (essentials)", "Percent": r.needs_pct, "Amount (₹/mo)": inc * r.needs_pct / 100.0},
        {"Category": "Wants (discretionary)", "Percent": r.wants_pct, "Amount (₹/mo)": inc * r.wants_pct / 100.0},
        {"Category": "Savings & investments", "Percent": r.savings_pct, "Amount (₹/mo)": inc * r.savings_pct / 100.0},
    ]
    df = pd.DataFrame(data)
    df["Amount (₹/mo)"] = df["Amount (₹/mo)"].round(0)
    return df


def budget_vs_actual_insight(
    monthly_income: float,
    monthly_expenses: float,
    monthly_investments: float,
    rule: BudgetRule | None = None,
) -> list[str]:
    """Compare rough 'needs' bucket to actual expenses + highlight gaps."""
    r = rule or BudgetRule()
    inc = max(0.0, safe_float(monthly_income))
    exp = max(0.0, safe_float(monthly_expenses))
    inv = max(0.0, safe_float(monthly_investments))
    if inc <= 0:
        return ["Enter a positive income to personalize the budget advice."]
    needs_guideline = inc * r.needs_pct / 100.0
    save_target = inc * r.savings_pct / 100.0
    lines: list[str] = []
    if exp > needs_guideline * 1.1:
        lines.append(
            f"Your expenses (**{exp:,.0f}**/mo) exceed the **50% needs** guide (**{needs_guideline:,.0f}**) — "
            f"review recurring bills or housing costs."
        )
    if inv < save_target * 0.75:
        lines.append(
            f"Savings/investments (**{inv:,.0f}**/mo) are below the **20%** target (**{save_target:,.0f}**) — "
            f"automate transfers on payday."
        )
    if not lines:
        lines.append("You are close to the 50/30/20 structure on income — keep tracking month to month.")
    return lines
