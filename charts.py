# charts.py — Plotly charts for wealth, SIP, and portfolio growth
"""Reusable Plotly figures for the Streamlit dashboard."""

from __future__ import annotations

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from financial_calculator import (
    calculate_sip_future_value,
    wealth_projection_series,
)
from utils import format_inr


def fig_wealth_projection(
    months: int,
    starting_savings: float,
    monthly_contribution: float,
    annual_return: float = 10.0,
) -> go.Figure:
    """Line chart: projected net worth over time."""
    mx, vals = wealth_projection_series(months, starting_savings, monthly_contribution, annual_return)
    years = mx / 12.0
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=years,
            y=vals,
            mode="lines",
            fill="tozeroy",
            name="Projected wealth",
            line=dict(color="#0d9488", width=2),
            fillcolor="rgba(13, 148, 136, 0.15)",
        )
    )
    fig.update_layout(
        title="Wealth projection (nominal)",
        xaxis_title="Years",
        yaxis_title="Amount (₹)",
        template="plotly_white",
        height=380,
        margin=dict(l=40, r=20, t=50, b=40),
        hovermode="x unified",
    )
    fig.update_yaxes(tickformat=",.0f")
    return fig


def fig_sip_growth(
    monthly_sip: float,
    years_list: list[int],
    annual_return: float = 12.0,
) -> go.Figure:
    """Bar chart: SIP corpus at different horizons."""
    corpi = []
    labels = []
    for y in years_list:
        res = calculate_sip_future_value(monthly_sip, annual_return, float(y))
        corpi.append(res.future_value)
        labels.append(f"{y} yr")
    fig = go.Figure(
        data=[
            go.Bar(
                x=labels,
                y=corpi,
                marker_color="#6366f1",
                text=[format_inr(v, compact=True) for v in corpi],
                textposition="outside",
            )
        ]
    )
    fig.update_layout(
        title=f"SIP growth @ {annual_return}% CAGR (illustrative)",
        yaxis_title="Corpus (₹)",
        template="plotly_white",
        height=360,
        margin=dict(l=40, r=20, t=50, b=40),
    )
    fig.update_yaxes(tickformat=",.0f")
    return fig


def fig_wealth_sip_horizons(
    monthly_sip: float,
    starting_principal: float = 0.0,
    annual_return: float = 12.0,
    horizons: tuple[int, ...] = (5, 10, 20),
) -> go.Figure:
    """
    Line chart: projected wealth through max(horizons) years at fixed SIP + lump sum.
    Highlights corpus at 5 / 10 / 20 year marks (per hackathon spec).
    """
    max_y = max(horizons)
    months = max_y * 12
    mx, vals = wealth_projection_series(months, starting_principal, monthly_sip, annual_return)
    years = mx / 12.0
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=years,
            y=vals,
            mode="lines",
            name=f"SIP {format_inr(monthly_sip)}/mo @ {annual_return}%",
            line=dict(color="#4f46e5", width=2.5),
        )
    )
    for h in horizons:
        if h <= max_y:
            idx = h * 12
            if idx < len(vals):
                fig.add_trace(
                    go.Scatter(
                        x=[h],
                        y=[vals[idx]],
                        mode="markers+text",
                        marker=dict(size=12, color="#0d9488"),
                        text=[f"{h}y: {format_inr(vals[idx], compact=True)}"],
                        textposition="top center",
                        name=f"{h}-year mark",
                        showlegend=False,
                    )
                )
    fig.update_layout(
        title=f"Wealth projection — monthly SIP @ {annual_return}% CAGR (illustrative)",
        xaxis_title="Years",
        yaxis_title="Projected value (₹)",
        template="plotly_white",
        height=420,
        margin=dict(l=40, r=20, t=50, b=40),
        hovermode="x unified",
    )
    fig.update_yaxes(tickformat=",.0f")
    return fig


def fig_monthly_breakdown(labels: list[str], values: list[float]) -> go.Figure:
    """Donut chart for income/expense or allocation."""
    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=0.55,
                marker=dict(colors=["#0ea5e9", "#f59e0b", "#10b981", "#8b5cf6", "#64748b"]),
            )
        ]
    )
    fig.update_layout(
        title="Monthly allocation (of surplus)",
        template="plotly_white",
        height=360,
        showlegend=True,
        margin=dict(l=20, r=20, t=50, b=20),
    )
    return fig


def fig_health_gauge(score: float) -> go.Figure:
    """Semi-circular gauge for money health score."""
    score = float(max(0, min(100, score)))
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=score,
            number={"suffix": "/100", "font": {"size": 36}},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": "#0d9488"},
                "steps": [
                    {"range": [0, 60], "color": "#fecaca"},
                    {"range": [60, 80], "color": "#fde68a"},
                    {"range": [80, 100], "color": "#bbf7d0"},
                ],
            },
            title={"text": "Money health"},
        )
    )
    fig.update_layout(height=280, template="plotly_white", margin=dict(t=40, b=10))
    return fig


def fig_portfolio_growth_scenarios(
    principal: float,
    monthly_add: float,
    months: int,
    scenarios: tuple[tuple[str, float], ...] = (
        ("Conservative 7%", 7.0),
        ("Balanced 10%", 10.0),
        ("Growth 12%", 12.0),
    ),
) -> go.Figure:
    """Multiple return scenarios on one chart."""
    fig = go.Figure()
    for name, ar in scenarios:
        mx, vals = wealth_projection_series(months, principal, monthly_add, ar)
        fig.add_trace(
            go.Scatter(
                x=mx / 12.0,
                y=vals,
                mode="lines",
                name=name,
            )
        )
    fig.update_layout(
        title="Portfolio growth scenarios",
        xaxis_title="Years",
        yaxis_title="Value (₹)",
        template="plotly_white",
        height=400,
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(l=40, r=20, t=50, b=40),
    )
    fig.update_yaxes(tickformat=",.0f")
    return fig


def fig_savings_rate_analysis(
    income: float,
    expenses: float,
    invest: float,
) -> go.Figure:
    """Stacked-style view: where income goes."""
    inc = max(0.01, float(income))
    exp = max(0.0, float(expenses))
    inv = max(0.0, float(invest))
    other = max(0.0, inc - exp - inv)
    fig = make_subplots(rows=1, cols=2, specs=[[{"type": "bar"}, {"type": "pie"}]])
    fig.add_trace(
        go.Bar(
            x=["Expenses", "Investments", "Remaining"],
            y=[exp, inv, other],
            marker_color=["#f97316", "#6366f1", "#94a3b8"],
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Pie(
            labels=["Expenses", "Investments", "Remaining"],
            values=[exp, inv, other],
            hole=0.4,
        ),
        row=1,
        col=2,
    )
    fig.update_layout(
        title_text="Savings rate analysis (monthly)",
        template="plotly_white",
        height=380,
        showlegend=False,
        margin=dict(l=40, r=20, t=60, b=40),
    )
    return fig
