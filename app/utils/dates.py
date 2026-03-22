"""Date helpers for deterministic time windows."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any


def parse_date(value: str | date | datetime) -> date:
    """Convert supported date-like values into a date."""

    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return datetime.fromisoformat(value).date()


def format_date(value: date) -> str:
    """Return an ISO-formatted date string."""

    return value.isoformat()


def build_week_windows(reference_date: str | date | datetime) -> dict[str, dict[str, Any]]:
    """Return current and previous seven-day windows ending on reference_date."""

    ref = parse_date(reference_date)
    current_start = ref - timedelta(days=6)
    previous_end = current_start - timedelta(days=1)
    previous_start = previous_end - timedelta(days=6)
    return {
        "current": {"start_date": format_date(current_start), "end_date": format_date(ref), "label": "current_week"},
        "previous": {
            "start_date": format_date(previous_start),
            "end_date": format_date(previous_end),
            "label": "previous_week",
        },
    }


def within_window(series, time_window: dict[str, Any]):
    """Return a boolean mask for rows within the provided ISO date window."""

    start = parse_date(time_window["start_date"])
    end = parse_date(time_window["end_date"])
    return (series.dt.date >= start) & (series.dt.date <= end)
