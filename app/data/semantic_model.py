"""Dataset views and schema manifest for planner and executor."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import duckdb
import pandas as pd

from app.config import get_settings
from app.data.loader import load_data


@dataclass(frozen=True)
class SemanticContext:
    """Curated views and schema manifest used by the planner/executor loop."""

    reference_date: str
    source: str
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
    """Build and cache views plus a schema-only manifest for planning."""

    bundle = load_data()
    raw_views = _read_raw_views()
    semantic_views = {"opportunities_enriched": bundle.crm.copy()}
    all_frames = {**raw_views, **semantic_views}
    schema_manifest: dict[str, Any] = {
        "reference_date": bundle.reference_date,
        "source": bundle.source,
        "views": [_schema_for_frame(name, frame) for name, frame in all_frames.items()],
    }
    return SemanticContext(
        reference_date=bundle.reference_date,
        source=bundle.source,
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
