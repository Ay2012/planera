"""Slicing and contributor tools for approved metrics."""

from __future__ import annotations

from typing import Any

import pandas as pd

from app.data.loader import load_data
from app.tools.metrics import InvalidMetricError
from app.utils.constants import SUPPORTED_DIMENSIONS, SUPPORTED_METRICS
from app.utils.dates import within_window


class InvalidDimensionError(ValueError):
    """Raised when a slice dimension is not approved."""


def _validate_inputs(metric_name: str, dimension: str) -> None:
    if metric_name not in SUPPORTED_METRICS:
        raise InvalidMetricError(f"Unsupported metric '{metric_name}'.")
    if dimension not in SUPPORTED_DIMENSIONS:
        raise InvalidDimensionError(f"Unsupported dimension '{dimension}'. Allowed dimensions: {sorted(SUPPORTED_DIMENSIONS)}")


def _pipeline_velocity_slice(dimension: str, time_window: dict[str, str]) -> list[dict[str, Any]]:
    bundle = load_data()
    crm = bundle.crm.copy()

    if dimension in {"segment", "owner"}:
        dataset = crm[crm["status"] == "won"].copy()
        dataset = dataset[within_window(dataset["close_date"], time_window)]
        grouped = (
            dataset.groupby(dimension)
            .agg(value=("pipeline_velocity_days", "mean"), sample_size=("deal_id", "count"))
            .reset_index()
        )
    elif dimension == "stage":
        dataset = crm[(crm["status"] == "open") & (crm["stage_age_days"].notna())].copy()
        grouped = (
            dataset.groupby(dimension)
            .agg(value=("stage_age_days", "mean"), sample_size=("deal_id", "count"))
            .reset_index()
        )
    elif dimension == "deal_age_bucket":
        dataset = crm[crm["status"] == "open"].copy()
        grouped = (
            dataset.groupby(dimension)
            .agg(value=("deal_id", "count"), sample_size=("deal_id", "count"))
            .reset_index()
        )
    else:
        dataset = crm[crm["status"] == "won"].copy()
        dataset = dataset[within_window(dataset["close_date"], time_window)]
        grouped = (
            dataset.groupby("plan_tier")
            .agg(value=("pipeline_velocity_days", "mean"), sample_size=("deal_id", "count"))
            .reset_index()
            .rename(columns={"plan_tier": dimension})
        )

    if grouped.empty:
        return []

    grouped["value"] = grouped["value"].round(2)
    grouped = grouped.sort_values(by="value", ascending=False).reset_index(drop=True)
    return grouped.to_dict(orient="records")


def _churn_rate_slice(dimension: str, time_window: dict[str, str]) -> list[dict[str, Any]]:
    bundle = load_data()
    if bundle.subscriptions is None:
        raise InvalidDimensionError("churn_rate slicing requires a subscriptions dataset, but none is loaded.")
    subscriptions = bundle.subscriptions.copy()
    crm = bundle.crm[["account_id", "segment", "owner"]].drop_duplicates(subset=["account_id"])
    subscriptions = subscriptions.merge(crm, on="account_id", how="left")

    if dimension in {"plan_tier", "segment", "owner"}:
        grouped = (
            subscriptions.groupby(dimension)
            .agg(churned=("churned", "sum"), total=("account_id", "count"))
            .reset_index()
        )
        grouped["value"] = ((grouped["churned"] / grouped["total"]) * 100).round(2)
        grouped["sample_size"] = grouped["total"]
        grouped = grouped[[dimension, "value", "sample_size"]]
        return grouped.sort_values(by="value", ascending=False).to_dict(orient="records")

    raise InvalidDimensionError(f"Dimension '{dimension}' is not supported for churn analysis in this MVP.")


def slice_metric(metric_name: str, dimension: str, time_window: dict[str, str]) -> dict[str, Any]:
    """Return a structured metric breakdown by an approved dimension."""

    _validate_inputs(metric_name, dimension)
    if metric_name == "pipeline_velocity":
        breakdown = _pipeline_velocity_slice(dimension, time_window)
    else:
        breakdown = _churn_rate_slice(dimension, time_window)

    return {
        "metric_name": metric_name,
        "dimension": dimension,
        "time_window": time_window,
        "breakdown": breakdown,
    }


def identify_top_contributors(metric_name: str, dimension: str, time_window: dict[str, str]) -> dict[str, Any]:
    """Return the highest-impact slice for a metric/dimension pair."""

    sliced = slice_metric(metric_name, dimension, time_window)
    breakdown = sliced["breakdown"]
    if not breakdown:
        return {
            "metric_name": metric_name,
            "dimension": dimension,
            "top_contributor": None,
            "breakdown": [],
        }

    top = breakdown[0]
    dimension_value = top.get(dimension)
    return {
        "metric_name": metric_name,
        "dimension": dimension,
        "top_contributor": {
            "dimension_value": dimension_value,
            "value": top["value"],
            "sample_size": top.get("sample_size", 0),
        },
        "breakdown": breakdown,
    }
