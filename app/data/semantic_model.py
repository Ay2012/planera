"""Registry-backed dataset views and schema manifest for planner and executor."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import duckdb
import pandas as pd

from app.data.registry import ensure_builtin_sources, get_registered_relation_names, get_registry_path, get_schema_manifest, load_relation_frames


@dataclass(frozen=True)
class SemanticContext:
    """Curated views and schema manifest used by the planner/executor loop."""

    reference_date: str
    source: str
    raw_views: dict[str, pd.DataFrame]
    semantic_views: dict[str, pd.DataFrame]
    schema_manifest: dict[str, Any]


def _source_ids_key(source_ids: list[str] | tuple[str, ...] | None) -> tuple[str, ...]:
    if not source_ids:
        return ()
    return tuple(sorted(source_ids))


@lru_cache(maxsize=32)
def _get_semantic_context_cached(source_ids_key: tuple[str, ...]) -> SemanticContext:
    ensure_builtin_sources()
    source_ids = list(source_ids_key) if source_ids_key else None
    manifest = get_schema_manifest(source_ids)
    frames = load_relation_frames(source_ids)
    primary_names = {relation["name"] for relation in manifest.get("relations", []) if relation.get("is_primary")}
    raw_views = {name: frame for name, frame in frames.items() if name not in primary_names}
    semantic_views = {name: frame for name, frame in frames.items() if name in primary_names}
    return SemanticContext(
        reference_date=manifest.get("reference_date", ""),
        source=manifest.get("source", ""),
        raw_views=raw_views,
        semantic_views=semantic_views,
        schema_manifest=manifest,
    )


def get_semantic_context(source_ids: list[str] | tuple[str, ...] | None = None) -> SemanticContext:
    """Build and cache views plus a schema-only manifest for planning."""

    return _get_semantic_context_cached(_source_ids_key(source_ids))


def clear_semantic_context_cache() -> None:
    """Clear cached registry-backed semantic contexts."""

    _get_semantic_context_cached.cache_clear()


def new_duckdb_connection(dataset_context: dict[str, Any] | None = None) -> duckdb.DuckDBPyConnection:
    """Create an in-memory DuckDB connection exposing only the requested relations."""

    ensure_builtin_sources()
    relation_names = [
        relation["name"]
        for relation in (dataset_context or {}).get("relations", [])
        if relation.get("name")
    ]
    if not relation_names:
        relation_names = [
            view["name"]
            for view in (dataset_context or {}).get("views", [])
            if view.get("name")
        ]
    if not relation_names:
        relation_names = get_registered_relation_names()

    conn = duckdb.connect(database=":memory:")
    registry_path = str(get_registry_path()).replace("'", "''")
    conn.execute(f"ATTACH '{registry_path}' AS registry_db")

    for relation_name in relation_names:
        escaped = relation_name.replace('"', '""')
        conn.execute(f'CREATE VIEW "{escaped}" AS SELECT * FROM registry_db."{escaped}"')
    return conn
