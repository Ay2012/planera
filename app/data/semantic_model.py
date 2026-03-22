"""Semantic dataset context and DuckDB view registration."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

from app.config import get_settings
from app.data.loader import load_data


@dataclass(frozen=True)
class SemanticContext:
    """Curated views and schema manifest used by the planner/executor loop."""

    reference_date: str
    raw_views: dict[str, pd.DataFrame]
    semantic_views: dict[str, pd.DataFrame]
    schema_manifest: dict[str, Any]


def _read_raw_views() -> dict[str, pd.DataFrame]:
    settings = get_settings()
    dataset_dir = settings.crm_dataset_dir
    return {
        "sales_pipeline": pd.read_csv(dataset_dir / "sales_pipeline.csv"),
        "accounts": pd.read_csv(dataset_dir / "accounts.csv"),
        "products": pd.read_csv(dataset_dir / "products.csv"),
        "sales_teams": pd.read_csv(dataset_dir / "sales_teams.csv"),
    }


def _schema_for_frame(name: str, frame: pd.DataFrame) -> dict[str, Any]:
    return {
        "name": name,
        "row_count": int(len(frame)),
        "columns": [{"name": col, "dtype": str(frame[col].dtype)} for col in frame.columns],
    }


@lru_cache(maxsize=1)
def get_semantic_context() -> SemanticContext:
    """Build and cache the semantic data context for planning and execution."""

    bundle = load_data()
    raw_views = _read_raw_views()
    semantic_views = {"opportunities_enriched": bundle.crm.copy()}
    opportunities = semantic_views["opportunities_enriched"]
    schema_manifest = {
        "reference_date": bundle.reference_date,
        "views": [_schema_for_frame(name, frame) for name, frame in {**raw_views, **semantic_views}.items()],
        "business_rules": {
            "metric": "pipeline_velocity = average(close_date - created_date) in days for won opportunities",
            "supported_dimensions": ["segment", "stage", "owner", "deal_age_bucket", "plan_tier"],
            "scope": "pipeline analytics only for the provided CRM sales dataset",
            "categorical_values": {
                "opportunities_enriched.status": sorted(opportunities["status"].dropna().astype(str).unique().tolist()),
                "opportunities_enriched.stage": sorted(opportunities["stage"].dropna().astype(str).unique().tolist()),
                "opportunities_enriched.segment": sorted(opportunities["segment"].dropna().astype(str).unique().tolist()),
            },
            "period_notes": {
                "current_period": "Boolean flag derived from close_date for the latest 7-day window ending on reference_date.",
                "previous_period": "Boolean flag derived from close_date for the prior 7-day window before current_period.",
                "important": "Use lowercase status values exactly as provided in the dataset.",
            },
        },
    }
    return SemanticContext(
        reference_date=bundle.reference_date,
        raw_views=raw_views,
        semantic_views=semantic_views,
        schema_manifest=schema_manifest,
    )


def new_duckdb_connection() -> duckdb.DuckDBPyConnection:
    """Create an in-memory DuckDB connection with curated views registered."""

    context = get_semantic_context()
    conn = duckdb.connect(database=":memory:")
    for name, frame in {**context.raw_views, **context.semantic_views}.items():
        conn.register(name, frame)
    return conn
