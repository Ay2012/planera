"""Comparison tools for approved metrics."""

from __future__ import annotations

from typing import Any

from app.tools.metrics import get_metric


def compare_metric(metric_name: str, current_window: dict[str, str], previous_window: dict[str, str]) -> dict[str, Any]:
    """Compare a metric between two explicit windows."""

    current = get_metric(metric_name, current_window["start_date"], current_window["end_date"])
    previous = get_metric(metric_name, previous_window["start_date"], previous_window["end_date"])
    delta = round(current["value"] - previous["value"], 2)
    delta_pct = round((delta / previous["value"]) * 100, 2) if previous["value"] else 0.0
    trend = "up" if delta > 0 else "down" if delta < 0 else "flat"
    return {
        "metric_name": metric_name,
        "current": current,
        "previous": previous,
        "delta": delta,
        "delta_pct": delta_pct,
        "trend": trend,
    }
