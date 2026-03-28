# utils.py — Shared helpers for Money Mentor AI
"""Utility functions: formatting, validation, and small helpers."""

from __future__ import annotations

import re
from typing import Any


def format_inr(amount: float, compact: bool = False) -> str:
    """Format Indian Rupee amounts with lakh/crore labels when useful."""
    if amount is None or (isinstance(amount, float) and amount != amount):  # NaN
        return "₹0"
    try:
        n = float(amount)
    except (TypeError, ValueError):
        return "₹0"
    if compact:
        if abs(n) >= 1e7:
            return f"₹{n / 1e7:.2f} Cr"
        if abs(n) >= 1e5:
            return f"₹{n / 1e5:.2f} L"
    # Indian numbering: last 3 digits, then groups of 2
    s = f"{abs(int(round(n))):,}"
    parts = s.split(",")
    if len(parts) > 1:
        last = parts[-1]
        rest = ",".join(parts[:-1])
        s = f"{rest},{last}" if rest else last
    sign = "-" if n < 0 else ""
    return f"{sign}₹{s}"


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return default


def sanitize_chat_input(text: str, max_len: int = 4000) -> str:
    """Strip control chars and limit length for API safety."""
    if not text:
        return ""
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", str(text))
    return text.strip()[:max_len]
