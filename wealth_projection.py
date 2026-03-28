# wealth_projection.py — Multi-horizon wealth paths (SIP + lump sum, offline)
"""Build time series for 5 / 10 / 20-year views at a fixed CAGR (default 12%)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from financial_calculator import wealth_projection_series


@dataclass
class HorizonCheckpoint:
    years: int
    corpus: float


@dataclass
class WealthProjectionPack:
    annual_return_pct: float
    monthly_sip: float
    starting_principal: float
    months_axis: np.ndarray
    values: np.ndarray
    checkpoints: list[HorizonCheckpoint]
    horizons_years: tuple[int, ...]


def build_projection_pack(
    monthly_sip: float,
    starting_principal: float = 0.0,
    annual_return_pct: float = 12.0,
    max_years: int = 20,
    mark_years: tuple[int, ...] = (5, 10, 20),
) -> WealthProjectionPack:
    """Full path 0…max_years and FV markers at mark_years (clipped to max_years)."""
    max_y = max(1, int(max_years))
    months = max_y * 12
    mx, vals = wealth_projection_series(months, starting_principal, monthly_sip, annual_return_pct)

    cps: list[HorizonCheckpoint] = []
    for y in mark_years:
        if y > max_y:
            continue
        idx = y * 12
        if idx < len(vals):
            cps.append(HorizonCheckpoint(years=int(y), corpus=float(vals[idx])))

    return WealthProjectionPack(
        annual_return_pct=float(annual_return_pct),
        monthly_sip=float(monthly_sip),
        starting_principal=float(starting_principal),
        months_axis=mx,
        values=vals,
        checkpoints=cps,
        horizons_years=tuple(y for y in mark_years if y <= max_y),
    )
