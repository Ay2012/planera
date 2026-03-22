"""Verification tools for approved metric outputs."""

from __future__ import annotations

from typing import Any

from app.data.loader import load_data
from app.tools.metrics import get_metric
from app.utils.constants import SUPPORTED_METRICS
from app.utils.dates import within_window


def verify_metric(metric_name: str, evidence: dict[str, Any] | list[dict[str, Any]]) -> dict[str, Any]:
    """Verify a metric using an independent recomputation and plausibility checks."""

    if metric_name not in SUPPORTED_METRICS:
        raise ValueError(f"Unsupported metric '{metric_name}'.")

    evidence_items = evidence if isinstance(evidence, list) else [evidence]
    current_metric = next((item for item in evidence_items if item.get("metric_name") == metric_name and "value" in item), None)
    time_window = current_metric.get("time_window", {}) if current_metric else {}
    start_date = time_window.get("start_date")
    end_date = time_window.get("end_date")

    bundle = load_data()
    checks: list[dict[str, Any]] = []

    if metric_name == "pipeline_velocity":
        crm = bundle.crm[bundle.crm["status"] == "won"].copy()
        if start_date and end_date:
            crm = crm[within_window(crm["close_date"], {"start_date": start_date, "end_date": end_date})]

        independent_value = round(float((crm["close_date"] - crm["created_date"]).dt.days.mean()), 2) if len(crm) else 0.0
        null_count = int(crm[["created_date", "close_date"]].isnull().sum().sum())
        plausible = 0 <= independent_value <= 120
        checks.extend(
            [
                {"check": "independent_recompute", "passed": current_metric is not None and independent_value == current_metric["value"]},
                {"check": "critical_nulls", "passed": null_count == 0, "null_count": null_count},
                {"check": "plausibility", "passed": plausible, "value": independent_value},
            ]
        )
    else:
        if bundle.subscriptions is None:
            raise ValueError("churn_rate verification is unavailable because no subscriptions dataset was provided.")
        subscriptions = bundle.subscriptions.copy()
        if start_date and end_date:
            subscriptions = subscriptions[
                within_window(subscriptions["subscription_start"], {"start_date": start_date, "end_date": end_date})
            ]
        total_accounts = len(subscriptions)
        independent_value = round((int(subscriptions["churned"].sum()) / total_accounts) * 100, 2) if total_accounts else 0.0
        null_count = int(subscriptions[["account_id", "plan_tier"]].isnull().sum().sum())
        plausible = 0 <= independent_value <= 100
        checks.extend(
            [
                {"check": "independent_recompute", "passed": current_metric is not None and independent_value == current_metric["value"]},
                {"check": "critical_nulls", "passed": null_count == 0, "null_count": null_count},
                {"check": "plausibility", "passed": plausible, "value": independent_value},
            ]
        )

    verified = all(check["passed"] for check in checks)
    return {
        "metric_name": metric_name,
        "verified": verified,
        "recomputed_value": independent_value,
        "checks": checks,
    }
