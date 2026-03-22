"""Metric retrieval tools."""

from __future__ import annotations

from typing import Any

from app.data.loader import load_data
from app.utils.constants import SUPPORTED_METRICS
from app.utils.dates import within_window


class InvalidMetricError(ValueError):
    """Raised when a metric outside the approved set is requested."""


class DataUnavailableError(ValueError):
    """Raised when the loaded dataset cannot support a requested metric."""


def _validate_metric(metric_name: str) -> None:
    if metric_name not in SUPPORTED_METRICS:
        raise InvalidMetricError(f"Unsupported metric '{metric_name}'. Allowed metrics: {sorted(SUPPORTED_METRICS)}")


def get_metric(metric_name: str, start_date: str | None = None, end_date: str | None = None) -> dict[str, Any]:
    """Return a structured top-line metric from trusted local datasets."""

    _validate_metric(metric_name)
    bundle = load_data()

    if metric_name == "pipeline_velocity":
        crm = bundle.crm[bundle.crm["status"] == "won"].copy()
        if start_date and end_date:
            mask = within_window(crm["close_date"], {"start_date": start_date, "end_date": end_date})
            crm = crm[mask]

        sample_size = int(len(crm))
        value = round(float(crm["pipeline_velocity_days"].mean()), 2) if sample_size else 0.0
        return {
            "metric_name": metric_name,
            "value": value,
            "unit": "days",
            "sample_size": sample_size,
            "time_window": {"start_date": start_date, "end_date": end_date},
        }

    if bundle.subscriptions is None:
        raise DataUnavailableError(
            "churn_rate is unavailable because no subscriptions dataset was provided. "
            "The current project data supports CRM and pipeline analysis only."
        )

    subscriptions = bundle.subscriptions.copy()
    if start_date and end_date:
        mask = within_window(subscriptions["subscription_start"], {"start_date": start_date, "end_date": end_date})
        subscriptions = subscriptions[mask]

    total_accounts = len(subscriptions)
    churned_accounts = int(subscriptions["churned"].sum())
    value = round((churned_accounts / total_accounts) * 100, 2) if total_accounts else 0.0
    return {
        "metric_name": metric_name,
        "value": value,
        "unit": "percent",
        "sample_size": int(total_accounts),
        "time_window": {"start_date": start_date, "end_date": end_date},
    }
