"""Dataset views and schema manifest for planner and executor."""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from itertools import combinations
from typing import Any

import duckdb
import pandas as pd

from app.data.loader import load_data
from app.schemas import SchemaColumn, SchemaConceptMapping, SchemaManifest, SchemaRelation, SchemaRelationship


@dataclass(frozen=True)
class SemanticContext:
    """Curated views and schema manifest used by the planner/executor loop."""

    reference_date: str
    source: str
    raw_views: dict[str, pd.DataFrame]
    semantic_views: dict[str, pd.DataFrame]
    schema_manifest: dict[str, Any]


_SEMANTIC_ALIAS_LEXICON: dict[str, list[str]] = {
    "owner": ["agent", "rep", "representative", "sales rep", "assignee"],
    "manager": ["manager", "lead", "supervisor", "team lead"],
    "regional_office": ["region", "regional office", "office", "territory"],
    "account_id": ["account", "customer", "client", "account identifier"],
    "deal_id": ["deal", "opportunity", "opportunity identifier"],
    "deal_value": ["revenue", "deal size", "amount", "value"],
    "stage": ["status stage", "pipeline stage"],
    "segment": ["customer segment", "market segment"],
    "pipeline_velocity_days": ["pipeline velocity", "cycle time", "sales cycle length"],
}


def _split_identifier(value: str) -> list[str]:
    cleaned = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value)
    tokens = [token.lower() for token in re.split(r"[^a-zA-Z0-9]+", cleaned) if token]
    return tokens


def _type_family(dtype: str) -> str:
    lower = dtype.lower()
    if any(token in lower for token in ("int", "float", "double", "decimal")):
        return "number"
    if "bool" in lower:
        return "boolean"
    if any(token in lower for token in ("datetime", "timestamp", "date")):
        return "datetime"
    if any(token in lower for token in ("object", "string", "category")):
        return "string"
    return "unknown"


def _semantic_hints(column_name: str) -> list[str]:
    tokens = _split_identifier(column_name)
    hints = {column_name, column_name.replace("_", " ")}
    hints.update(tokens)
    if column_name.endswith("_id"):
        base = column_name[: -len("_id")].replace("_", " ").strip()
        if base:
            hints.add(f"{base} id")
            hints.add(f"{base} identifier")

    for key, aliases in _SEMANTIC_ALIAS_LEXICON.items():
        key_tokens = set(_split_identifier(key))
        if column_name == key or key_tokens.issubset(set(tokens)):
            hints.update(aliases)

    return sorted(hint for hint in hints if hint)


def _is_identifier_column(column_name: str, series: pd.Series) -> bool:
    lowered = column_name.lower()
    if lowered == "id" or lowered.endswith("_id"):
        return True
    non_null = series.dropna()
    return bool(len(non_null) == len(series) and len(non_null) > 0 and non_null.nunique(dropna=False) == len(series))


def _infer_grain(name: str, frame: pd.DataFrame, identifier_columns: list[str]) -> str:
    if identifier_columns:
        primary = identifier_columns[0]
        if primary.lower().endswith("_id"):
            entity = primary[: -len("_id")].replace("_", " ").strip()
            if entity:
                return f"Approximately one row per {entity}"
        return f"Rows can be keyed by {primary}"
    return f"Rows represent records in {name}"


def _build_semantic_mappings(columns: list[SchemaColumn]) -> list[SchemaConceptMapping]:
    concept_to_columns: dict[str, set[str]] = {}
    for column in columns:
        for hint in column.semantic_hints:
            normalized_hint = hint.strip().lower()
            if not normalized_hint or normalized_hint == column.name.lower():
                continue
            concept_to_columns.setdefault(normalized_hint, set()).add(column.name)

    mappings: list[SchemaConceptMapping] = []
    for concept, mapped_columns in sorted(concept_to_columns.items()):
        if len(concept) < 4:
            continue
        mappings.append(
            SchemaConceptMapping(
                concept=concept,
                columns=sorted(mapped_columns),
            )
        )
    return mappings[:20]


def _derive_sources_for_column(
    column_name: str,
    field_origin: str,
    source_lookup: dict[str, list[str]],
) -> list[str]:
    if field_origin != "derived":
        return []
    return [f"{relation}.{column_name}" for relation in source_lookup.get(column_name, [])][:4]


def _relation_for_frame(
    name: str,
    frame: pd.DataFrame,
    kind: str = "view",
    field_origin: str = "source_backed",
    source_lookup: dict[str, list[str]] | None = None,
) -> SchemaRelation:
    columns: list[SchemaColumn] = []
    identifier_columns: list[str] = []
    time_columns: list[str] = []
    measure_columns: list[str] = []
    dimension_columns: list[str] = []
    source_lookup = source_lookup or {}

    for column_name in frame.columns:
        dtype = str(frame[column_name].dtype)
        family = _type_family(dtype)
        column = SchemaColumn(
            name=column_name,
            dtype=dtype,
            type_family=family,
            field_origin=field_origin,
            derived_from=_derive_sources_for_column(column_name, field_origin, source_lookup),
            semantic_hints=_semantic_hints(column_name),
        )
        columns.append(column)

        if _is_identifier_column(column_name, frame[column_name]):
            identifier_columns.append(column_name)
        if family == "datetime":
            time_columns.append(column_name)
        elif family == "number":
            measure_columns.append(column_name)
        else:
            dimension_columns.append(column_name)

    return SchemaRelation(
        name=name,
        kind=kind,
        row_count=int(len(frame)),
        grain=_infer_grain(name, frame, identifier_columns),
        identifier_columns=identifier_columns,
        time_columns=time_columns,
        measure_columns=measure_columns,
        dimension_columns=dimension_columns,
        columns=columns,
        semantic_mappings=_build_semantic_mappings(columns),
    )


def _relationship_type(left: SchemaRelation, right: SchemaRelation, join_keys: list[str]) -> str:
    left_unique = all(key in left.identifier_columns for key in join_keys)
    right_unique = all(key in right.identifier_columns for key in join_keys)
    if left_unique and right_unique:
        return "one_to_one"
    if right_unique:
        return "many_to_one"
    if left_unique:
        return "one_to_many"
    return "many_to_many"


def _build_relationships(relations: list[SchemaRelation]) -> list[SchemaRelationship]:
    relationships: list[SchemaRelationship] = []
    for left, right in combinations(relations, 2):
        left_columns = {column.name for column in left.columns}
        right_columns = {column.name for column in right.columns}
        join_keys = sorted(
            column
            for column in (left_columns & right_columns)
            if column.endswith("_id") or column in left.identifier_columns or column in right.identifier_columns
        )
        if not join_keys:
            continue
        relationships.append(
            SchemaRelationship(
                left_relation=left.name,
                right_relation=right.name,
                left_on=join_keys,
                right_on=join_keys,
                relationship_type=_relationship_type(left, right, join_keys),
            )
        )
    return relationships


@lru_cache(maxsize=1)
def get_semantic_context() -> SemanticContext:
    """Build and cache views plus a schema-only manifest for planning."""

    bundle = load_data()
    raw_views = {name: frame.copy() for name, frame in bundle.raw_views.items()}
    semantic_views = {"opportunities_enriched": bundle.crm.copy()}
    source_lookup: dict[str, list[str]] = {}
    for relation_name, frame in raw_views.items():
        for column_name in frame.columns:
            source_lookup.setdefault(column_name, []).append(relation_name)

    relations = [
        *[
            _relation_for_frame(name, frame, kind="table", field_origin="source_backed")
            for name, frame in raw_views.items()
        ],
        *[
            _relation_for_frame(
                name,
                frame,
                kind="view",
                field_origin="derived",
                source_lookup=source_lookup,
            )
            for name, frame in semantic_views.items()
        ],
    ]
    relationships = _build_relationships(relations)
    schema_manifest = SchemaManifest(
        reference_date=bundle.reference_date,
        source=bundle.source,
        dialect="duckdb",
        relations=relations,
        relationships=relationships,
        views=[
            {
                "name": relation.name,
                "row_count": relation.row_count,
                "columns": [{"name": column.name, "dtype": column.dtype} for column in relation.columns],
            }
            for relation in relations
        ],
    ).model_dump()
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
