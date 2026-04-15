"""Build the raw-schema planner input from persisted upload facts."""

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
import re
from typing import Any

import pandas as pd

from app.data.registry import (
    get_source_columns,
    get_source_links,
    get_source_records,
    get_source_relations,
    load_relation_frames,
)
from app.schemas import PlannerColumn, PlannerInput, PlannerRelationship, PlannerRelationshipKey, PlannerSource, PlannerTable


_SYSTEM_COLUMNS = {"record_id", "parent_record_id", "ordinal"}
_SUPPORTED_SOURCE_FORMATS = {"csv", "tsv", "json"}
_COUNT_ONLY_AGGREGATIONS = ["count"]
_MEASURE_AGGREGATIONS = ["count", "sum", "avg", "min", "max"]


def _source_description(metadata: dict[str, Any]) -> str | None:
    for key in ("description", "source_description"):
        value = metadata.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _raw_relation_name(relation: dict[str, Any], source_name: str) -> str:
    lineage = relation.get("lineage") or {}
    raw_name = lineage.get("raw_name")
    if isinstance(raw_name, str) and raw_name.strip():
        return raw_name.strip()

    stem = Path(source_name).stem
    json_path = lineage.get("json_path")
    if isinstance(json_path, str) and json_path and json_path != "$":
        return f"{stem}.{json_path}"
    return stem


def _column_display_name(column: dict[str, Any], duplicate_originals: Counter[str]) -> str:
    normalized = column["column_name"]
    if normalized in _SYSTEM_COLUMNS:
        return normalized

    original = str(column.get("original_name") or normalized)
    source_path = str(column.get("source_path") or original)
    if "." in source_path and duplicate_originals[original] > 1:
        return source_path
    return original


def _is_unique_non_null(series: pd.Series | None) -> bool:
    if series is None:
        return False
    if series.isna().any():
        return False
    return bool(len(series) > 0 and series.nunique(dropna=False) == len(series))


def _is_identifier_column(column: dict[str, Any], series: pd.Series | None) -> bool:
    candidates = [
        str(column.get("column_name") or ""),
        str(column.get("original_name") or ""),
        str(column.get("source_path") or ""),
    ]
    lowered = [candidate.strip().lower() for candidate in candidates if candidate]
    if any(value == "id" or value.endswith("_id") or value.endswith(".id") for value in lowered):
        return True
    if not _is_unique_non_null(series):
        return False

    family = str(column.get("type_family") or "unknown")
    if family not in {"string", "unknown"}:
        return False

    key_like_tokens = {"key", "code", "uuid", "guid", "identifier", "reference", "ref", "number", "num", "no"}
    tokenized = {
        token
        for candidate in lowered
        for token in re.split(r"[^a-z0-9]+", candidate)
        if token
    }
    return bool(tokenized & key_like_tokens)


def _is_time_column(column: dict[str, Any]) -> bool:
    if column.get("type_family") == "datetime":
        return True
    candidates = [
        str(column.get("column_name") or ""),
        str(column.get("original_name") or ""),
        str(column.get("source_path") or ""),
    ]
    lowered = " ".join(candidate.lower() for candidate in candidates if candidate)
    return any(token in lowered for token in ("date", "time", "timestamp")) or any(
        candidate.strip().lower().endswith("_at") for candidate in candidates if candidate
    )


def _semantic_role(column: dict[str, Any], series: pd.Series | None) -> str:
    if column["column_name"] in _SYSTEM_COLUMNS:
        return "identifier"
    if _is_identifier_column(column, series):
        return "identifier"
    if _is_time_column(column):
        return "time"

    family = str(column.get("type_family") or "unknown")
    if family == "boolean":
        return "boolean"
    if family == "number":
        return "measure"
    if family == "string":
        return "dimension"
    return "unknown"


def _allowed_aggregations(role: str) -> list[str]:
    if role == "measure":
        return list(_MEASURE_AGGREGATIONS)
    if role in {"identifier", "time", "dimension", "boolean"}:
        return list(_COUNT_ONLY_AGGREGATIONS)
    return []


def _derive_grain(table_name: str, identifier_columns: list[str]) -> str:
    if identifier_columns:
        primary = identifier_columns[0]
        if primary.lower().endswith("_id"):
            entity = primary[: -len("_id")].replace("_", " ").strip()
            if entity:
                return f"Approximately one row per {entity}"
        return f"Rows can be keyed by {primary}"
    return f"Rows represent records in {table_name}"


def _derive_table_purpose(table_name: str, grain: str, parent_relation: str | None) -> str:
    if parent_relation:
        return f"{grain}. This table captures nested records linked to a parent table."
    return f"{grain}. This table captures records for {table_name}."


def _keys_unique(frame: pd.DataFrame | None, columns: list[str]) -> bool:
    if frame is None or not columns:
        return False
    if any(column not in frame.columns for column in columns):
        return False
    subset = frame[columns]
    if subset.isna().any().any():
        return False
    return bool(len(subset) > 0 and len(subset.drop_duplicates()) == len(subset))


def _cardinality_for_link(
    left_frame: pd.DataFrame | None,
    right_frame: pd.DataFrame | None,
    join_keys: list[dict[str, str]],
) -> str:
    left_columns = [row["left_column"] for row in join_keys if row.get("left_column")]
    right_columns = [row["right_column"] for row in join_keys if row.get("right_column")]
    left_unique = _keys_unique(left_frame, left_columns)
    right_unique = _keys_unique(right_frame, right_columns)
    if left_unique and right_unique:
        return "one_to_one"
    if left_unique and not right_unique:
        return "one_to_many"
    if not left_unique and right_unique:
        return "many_to_one"
    return "unknown"


def _join_safety(link_type: str, cardinality: str) -> str:
    if link_type == "parent_child" or cardinality == "one_to_many":
        return "aggregate_child_before_join"
    if cardinality in {"one_to_one", "many_to_one"}:
        return "safe_raw_join"
    return "manual_review_required"


def _confirmed_by(link_type: str, is_explicit: bool) -> str:
    if link_type == "parent_child":
        return "json_nesting"
    if is_explicit:
        return "user_link"
    return "registry_rule"


def _build_planner_columns(
    raw_table_name: str,
    relation_columns: list[dict[str, Any]],
    frame: pd.DataFrame | None,
) -> tuple[list[PlannerColumn], dict[str, str]]:
    duplicate_originals = Counter(
        str(column.get("original_name") or column["column_name"])
        for column in relation_columns
        if column["column_name"] not in _SYSTEM_COLUMNS
    )
    planner_columns: list[PlannerColumn] = []
    normalized_to_raw: dict[str, str] = {}

    for column in relation_columns:
        normalized_name = column["column_name"]
        raw_name = _column_display_name(column, duplicate_originals)
        normalized_to_raw[normalized_name] = raw_name

        if normalized_name in _SYSTEM_COLUMNS:
            continue

        series = frame[normalized_name] if frame is not None and normalized_name in frame.columns else None
        role = _semantic_role(column, series)
        allowed_aggregations = _allowed_aggregations(role)
        planner_columns.append(
            PlannerColumn(
                table_name=raw_table_name,
                column_name=raw_name,
                data_type=column["dtype"],
                nullable=bool(column["nullable"]),
                source_path=column.get("source_path"),
                source_description=None,
                semantic_role=role,
                filterable=role != "unknown",
                groupable=role in {"identifier", "time", "dimension", "boolean"},
                aggregatable=bool(allowed_aggregations),
                allowed_aggregations=allowed_aggregations,
            )
        )

    return planner_columns, normalized_to_raw


def build_planner_input(query: str, source_ids: list[str] | None = None) -> PlannerInput:
    """Return the full raw-schema planner contract for the requested uploads."""

    source_rows = get_source_records(source_ids)
    relation_rows = get_source_relations(source_ids)
    column_rows = get_source_columns(source_ids)
    link_rows = get_source_links(source_ids)
    frames = load_relation_frames(source_ids)

    relations_by_source: dict[str, list[dict[str, Any]]] = defaultdict(list)
    columns_by_relation: dict[str, list[dict[str, Any]]] = defaultdict(list)
    normalized_to_raw_table: dict[str, str] = {}
    normalized_to_raw_column: dict[str, dict[str, str]] = {}

    for relation in relation_rows:
        relations_by_source[relation["source_id"]].append(relation)
    for column in column_rows:
        columns_by_relation[column["relation_name"]].append(column)

    planner_sources: list[PlannerSource] = []
    for source in source_rows:
        source_format = str(source["source_format"]).lower()
        if source_format not in _SUPPORTED_SOURCE_FORMATS:
            raise ValueError(f"Unsupported planner source format: {source_format}")

        tables: list[PlannerTable] = []
        source_relations = relations_by_source.get(source["source_id"], [])
        source_relations.sort(key=lambda row: (not row["is_primary"], _raw_relation_name(row, source["source_name"]).lower()))

        for relation in source_relations:
            raw_table_name = _raw_relation_name(relation, source["source_name"])
            normalized_to_raw_table[relation["relation_name"]] = raw_table_name

            relation_columns = sorted(columns_by_relation.get(relation["relation_name"], []), key=lambda row: row["ordinal"])
            frame = frames.get(relation["relation_name"])
            planner_columns, column_name_map = _build_planner_columns(
                raw_table_name,
                relation_columns,
                frame,
            )
            normalized_to_raw_column[relation["relation_name"]] = column_name_map

            identifier_columns = [column.column_name for column in planner_columns if column.semantic_role == "identifier"]
            time_columns = [column.column_name for column in planner_columns if column.semantic_role == "time"]
            measure_columns = [column.column_name for column in planner_columns if column.semantic_role == "measure"]
            dimension_columns = [column.column_name for column in planner_columns if column.semantic_role == "dimension"]
            filterable_columns = [column.column_name for column in planner_columns if column.filterable]
            groupable_columns = [column.column_name for column in planner_columns if column.groupable]
            aggregatable_columns = [column.column_name for column in planner_columns if column.aggregatable]
            grain = _derive_grain(raw_table_name, identifier_columns)

            tables.append(
                PlannerTable(
                    source_id=source["source_id"],
                    table_name=raw_table_name,
                    kind="table",
                    row_count=relation["row_count"],
                    source_description=None,
                    grain=grain,
                    table_purpose=_derive_table_purpose(raw_table_name, grain, relation["parent_relation"]),
                    identifier_columns=identifier_columns,
                    time_columns=time_columns,
                    measure_columns=measure_columns,
                    dimension_columns=dimension_columns,
                    filterable_columns=filterable_columns,
                    groupable_columns=groupable_columns,
                    aggregatable_columns=aggregatable_columns,
                    columns=planner_columns,
                )
            )

        planner_sources.append(
            PlannerSource(
                source_id=source["source_id"],
                source_name=source["source_name"],
                source_format=source_format,
                source_description=_source_description(source["metadata"]),
                tables=tables,
            )
        )

    planner_relationships: list[PlannerRelationship] = []
    for link in link_rows:
        left_relation_name = link["left_relation_name"]
        right_relation_name = link["right_relation_name"]
        cardinality = _cardinality_for_link(
            frames.get(left_relation_name),
            frames.get(right_relation_name),
            link["join_keys"],
        )
        planner_relationships.append(
            PlannerRelationship(
                left_source_id=link["left_source_id"],
                left_table=normalized_to_raw_table.get(left_relation_name, left_relation_name),
                right_source_id=link["right_source_id"],
                right_table=normalized_to_raw_table.get(right_relation_name, right_relation_name),
                relationship_type="parent_child" if link["link_type"] == "parent_child" else "explicit",
                cardinality=cardinality,
                join_keys=[
                    PlannerRelationshipKey(
                        left_column=normalized_to_raw_column.get(left_relation_name, {}).get(row["left_column"], row["left_column"]),
                        right_column=normalized_to_raw_column.get(right_relation_name, {}).get(row["right_column"], row["right_column"]),
                    )
                    for row in link["join_keys"]
                ],
                join_safety=_join_safety(link["link_type"], cardinality),
                confirmed_by=_confirmed_by(link["link_type"], link["is_explicit"]),
            )
        )

    return PlannerInput(
        user_query=query,
        execution_dialect="duckdb",
        sources=planner_sources,
        relationships=planner_relationships,
    )
