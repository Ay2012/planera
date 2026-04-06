"""Persistent DuckDB-backed source registry and source-package ingestion."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from typing import Any
from uuid import uuid4

import duckdb
import pandas as pd

from app.config import get_settings
from app.schemas import SchemaColumn, SchemaConceptMapping, SchemaJoinKey, SchemaManifest, SchemaRelation, UploadedAsset


_SOURCES_TABLE = "__planera_registry_data_sources"
_RELATIONS_TABLE = "__planera_registry_source_relations"
_COLUMNS_TABLE = "__planera_registry_source_columns"
_LINKS_TABLE = "__planera_registry_source_links"
_SYSTEM_COLUMNS = {"record_id", "parent_record_id", "ordinal"}
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


@dataclass(frozen=True)
class SourceLinkPackage:
    """Explicit relation link stored in the registry."""

    left_source_id: str
    left_relation_name: str
    right_source_id: str
    right_relation_name: str
    join_keys: list[dict[str, str]]
    link_type: str = "explicit"
    is_explicit: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RelationPackage:
    """One materialized relation plus its normalized schema metadata."""

    relation: SchemaRelation
    frame: pd.DataFrame


@dataclass(frozen=True)
class SourcePackage:
    """Unified internal representation for uploaded or built-in sources."""

    source_id: str
    source_name: str
    source_slug: str
    source_kind: str
    source_format: str
    origin: str
    file_name: str
    file_type: str
    size_bytes: int
    raw_payload: bytes | None
    relations: list[RelationPackage]
    links: list[SourceLinkPackage] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def primary_relation_name(self) -> str:
        primary = next((item.relation.name for item in self.relations if item.relation.is_primary), self.relations[0].relation.name)
        return primary


def get_registry_path() -> Path:
    """Return the on-disk DuckDB registry path."""

    return get_settings().registry_path


def _connect_registry(read_only: bool = False) -> duckdb.DuckDBPyConnection:
    path = get_registry_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    if read_only and not path.exists():
        conn = duckdb.connect(database=str(path), read_only=False)
        _ensure_registry_tables(conn)
        return conn
    conn = duckdb.connect(database=str(path), read_only=read_only)
    if not read_only:
        _ensure_registry_tables(conn)
    return conn


def _ensure_registry_tables(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {_SOURCES_TABLE} (
            source_id TEXT PRIMARY KEY,
            source_name TEXT,
            source_slug TEXT,
            source_kind TEXT,
            source_format TEXT,
            origin TEXT,
            file_name TEXT,
            file_type TEXT,
            size_bytes BIGINT,
            created_at TEXT,
            content_hash TEXT,
            primary_relation_name TEXT,
            relation_count INTEGER,
            row_count INTEGER,
            status TEXT,
            raw_payload BLOB,
            metadata_json TEXT
        )
        """
    )
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {_RELATIONS_TABLE} (
            relation_name TEXT PRIMARY KEY,
            source_id TEXT,
            kind TEXT,
            is_primary BOOLEAN,
            parent_relation TEXT,
            row_count BIGINT,
            grain TEXT,
            identifier_columns_json TEXT,
            time_columns_json TEXT,
            measure_columns_json TEXT,
            dimension_columns_json TEXT,
            lineage_json TEXT
        )
        """
    )
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {_COLUMNS_TABLE} (
            source_id TEXT,
            relation_name TEXT,
            ordinal INTEGER,
            column_name TEXT,
            dtype TEXT,
            type_family TEXT,
            original_name TEXT,
            source_path TEXT,
            nullable BOOLEAN,
            semantic_hints_json TEXT
        )
        """
    )
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {_LINKS_TABLE} (
            link_id TEXT PRIMARY KEY,
            left_source_id TEXT,
            left_relation_name TEXT,
            right_source_id TEXT,
            right_relation_name TEXT,
            link_type TEXT,
            is_explicit BOOLEAN,
            join_keys_json TEXT,
            metadata_json TEXT
        )
        """
    )


def clear_source_registry() -> None:
    """Remove the persisted registry database."""

    path = get_registry_path()
    if path.exists():
        path.unlink()
    from app.data.semantic_model import clear_semantic_context_cache

    clear_semantic_context_cache()


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _short_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:8]}"


def _slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().lower()).strip("_")
    cleaned = re.sub(r"_+", "_", cleaned)
    return cleaned[:48] or "source"


def _safe_identifier(value: str) -> str:
    normalized = _slugify(value)
    if normalized[0].isdigit():
        return f"c_{normalized}"
    return normalized


def _derive_file_type(filename: str, source_format: str) -> str:
    suffix = Path(filename).suffix.lstrip(".").upper()
    if suffix:
        return suffix
    return source_format.upper() or "FILE"


def _split_identifier(value: str) -> list[str]:
    cleaned = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value)
    return [token.lower() for token in re.split(r"[^a-zA-Z0-9]+", cleaned) if token]


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


def _semantic_hints(column_name: str, original_name: str = "", source_path: str = "") -> list[str]:
    tokens = _split_identifier(column_name)
    hints = {column_name, column_name.replace("_", " ")}
    if original_name:
        hints.add(original_name)
        hints.add(original_name.replace("_", " "))
    if source_path:
        hints.add(source_path)
        hints.add(source_path.replace(".", " "))
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
        mappings.append(SchemaConceptMapping(concept=concept, columns=sorted(mapped_columns)))
    return mappings[:20]


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


def _normalize_scalar(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, (datetime, pd.Timestamp)):
        return pd.Timestamp(value)
    return json.dumps(value, default=str)


def _parse_text_bool(series: pd.Series) -> pd.Series | None:
    non_null = series.dropna().astype(str).str.strip().str.lower()
    if non_null.empty:
        return None
    if set(non_null.unique()).issubset({"true", "false"}):
        mapped = series.map(
            lambda item: None
            if pd.isna(item)
            else str(item).strip().lower() == "true"
        )
        return mapped.astype("boolean")
    return None


def _parse_text_numeric(series: pd.Series) -> pd.Series | None:
    non_null = series.dropna()
    if non_null.empty:
        return None
    parsed = pd.to_numeric(non_null, errors="coerce")
    if parsed.notna().sum() != len(non_null):
        return None
    return pd.to_numeric(series, errors="coerce")


def _parse_text_datetime(column_name: str, series: pd.Series) -> pd.Series | None:
    lowered_name = column_name.lower()
    if not (
        any(token in lowered_name for token in ("date", "time", "timestamp"))
        or lowered_name.endswith("_at")
        or lowered_name == "at"
    ):
        return None
    non_null = series.dropna()
    if non_null.empty:
        return None
    parsed = pd.to_datetime(non_null, errors="coerce", utc=False)
    if parsed.notna().sum() / len(non_null) < 0.8:
        return None
    return pd.to_datetime(series, errors="coerce", utc=False)


def _coerce_frame_types(frame: pd.DataFrame) -> pd.DataFrame:
    coerced = frame.copy()
    for column_name in coerced.columns:
        series = coerced[column_name]
        if pd.api.types.is_bool_dtype(series) or pd.api.types.is_numeric_dtype(series) or pd.api.types.is_datetime64_any_dtype(series):
            continue
        if not (pd.api.types.is_object_dtype(series) or pd.api.types.is_string_dtype(series)):
            continue

        parsed = _parse_text_bool(series)
        if parsed is None:
            parsed = _parse_text_numeric(series)
        if parsed is None:
            parsed = _parse_text_datetime(str(column_name), series)
        if parsed is not None:
            coerced[column_name] = parsed
    return coerced.convert_dtypes()


def _rename_system_columns(frame: pd.DataFrame) -> pd.DataFrame:
    renamed = frame.copy()
    next_names: dict[str, str] = {}
    for column in renamed.columns:
        safe_name = _safe_identifier(str(column))
        candidate = safe_name
        if candidate in _SYSTEM_COLUMNS:
            candidate = f"{candidate}_value"
        counter = 2
        while candidate in next_names.values():
            candidate = f"{safe_name}_{counter}"
            counter += 1
        next_names[column] = candidate
    return renamed.rename(columns=next_names)


def _ensure_record_id(frame: pd.DataFrame) -> pd.DataFrame:
    framed = frame.copy()
    if "record_id" in framed.columns:
        framed = framed.rename(columns={"record_id": "record_id_value"})
    framed.insert(0, "record_id", [f"record_{index + 1}" for index in range(len(framed))])
    return framed


def _schema_relation_for_frame(
    *,
    relation_name: str,
    source_id: str,
    source_name: str,
    frame: pd.DataFrame,
    kind: str,
    is_primary: bool,
    parent_relation: str | None,
    join_keys: list[SchemaJoinKey],
    lineage: dict[str, Any],
    column_paths: dict[str, dict[str, str]] | None = None,
) -> SchemaRelation:
    column_paths = column_paths or {}
    columns: list[SchemaColumn] = []
    identifier_columns: list[str] = []
    time_columns: list[str] = []
    measure_columns: list[str] = []
    dimension_columns: list[str] = []

    for column_name in frame.columns:
        dtype = str(frame[column_name].dtype)
        family = _type_family(dtype)
        path_meta = column_paths.get(str(column_name), {})
        column = SchemaColumn(
            name=str(column_name),
            dtype=dtype,
            type_family=family,
            original_name=path_meta.get("original_name", str(column_name)),
            source_path=path_meta.get("source_path", str(column_name)),
            nullable=bool(frame[column_name].isna().any()),
            semantic_hints=_semantic_hints(
                str(column_name),
                original_name=path_meta.get("original_name", str(column_name)),
                source_path=path_meta.get("source_path", str(column_name)),
            ),
        )
        columns.append(column)

        if _is_identifier_column(str(column_name), frame[column_name]):
            identifier_columns.append(str(column_name))
        if family == "datetime":
            time_columns.append(str(column_name))
        elif family == "number":
            measure_columns.append(str(column_name))
        else:
            dimension_columns.append(str(column_name))

    return SchemaRelation(
        name=relation_name,
        kind=kind,
        source_id=source_id,
        source_name=source_name,
        is_primary=is_primary,
        parent_relation=parent_relation,
        row_count=int(len(frame)),
        grain=_infer_grain(relation_name, frame, identifier_columns),
        identifier_columns=identifier_columns,
        time_columns=time_columns,
        measure_columns=measure_columns,
        dimension_columns=dimension_columns,
        join_keys=join_keys,
        lineage=lineage,
        columns=columns,
        semantic_mappings=_build_semantic_mappings(columns),
    )


def _source_filter_sql(source_ids: list[str] | None) -> tuple[str, list[str]]:
    if not source_ids:
        return "", []
    placeholders = ", ".join(["?"] * len(source_ids))
    return f" WHERE source_id IN ({placeholders})", list(source_ids)


def _link_filter_sql(source_ids: list[str] | None) -> tuple[str, list[str]]:
    if not source_ids:
        return "", []
    placeholders = ", ".join(["?"] * len(source_ids))
    return (
        f" WHERE left_source_id IN ({placeholders}) AND right_source_id IN ({placeholders})",
        list(source_ids) + list(source_ids),
    )


def _read_uploaded_frame(filename: str, content: bytes) -> pd.DataFrame:
    if not content:
        raise ValueError("Uploaded file is empty.")

    suffix = Path(filename).suffix.lower()
    buffer = BytesIO(content)
    try:
        if suffix == ".csv":
            return pd.read_csv(buffer)
    except Exception as exc:  # pragma: no cover - pandas errors vary
        raise ValueError(f"Could not parse {filename} as a structured text dataset.") from exc

    raise ValueError("Only CSV and JSON uploads are currently supported.")


def _build_uploaded_asset(package: SourcePackage) -> UploadedAsset:
    primary = next(item for item in package.relations if item.relation.is_primary)
    visible_columns = [column.name for column in primary.relation.columns if column.name != "record_id"]
    relation_count = len(package.relations)
    summary = (
        f"Persisted {primary.relation.row_count} rows across {len(visible_columns)} columns"
        f" into {relation_count} relation{'s' if relation_count != 1 else ''}. "
        f"Primary relation: {package.primary_relation_name}."
    )
    return UploadedAsset(
        id=package.source_id,
        name=package.file_name,
        type=package.file_type,
        source=package.origin,
        sizeLabel=_bytes_to_size(package.size_bytes),
        uploadedAt=_now_iso(),
        status="verified",
        rows=primary.relation.row_count,
        columns=len(visible_columns),
        relationCount=relation_count,
        primaryRelationName=package.primary_relation_name,
        summary=summary,
    )


def _bytes_to_size(num_bytes: int) -> str:
    if num_bytes < 1024:
        return f"{num_bytes} B"
    if num_bytes < 1024 * 1024:
        return f"{num_bytes / 1024:.1f} KB"
    if num_bytes < 1024 * 1024 * 1024:
        return f"{num_bytes / (1024 * 1024):.1f} MB"
    return f"{num_bytes / (1024 * 1024 * 1024):.1f} GB"


def _persist_source_package(conn: duckdb.DuckDBPyConnection, package: SourcePackage) -> None:
    created_at = _now_iso()
    conn.execute("BEGIN TRANSACTION")
    try:
        for relation in package.relations:
            conn.execute(f'DELETE FROM {_RELATIONS_TABLE} WHERE relation_name = ?', [relation.relation.name])
            conn.execute(f'DELETE FROM {_COLUMNS_TABLE} WHERE relation_name = ?', [relation.relation.name])
            temp_name = f"tmp_{uuid4().hex[:8]}"
            conn.register(temp_name, relation.frame)
            conn.execute(f'DROP TABLE IF EXISTS "{relation.relation.name}"')
            conn.execute(f'CREATE TABLE "{relation.relation.name}" AS SELECT * FROM "{temp_name}"')
            conn.unregister(temp_name)
            conn.execute(
                f"""
                INSERT INTO {_RELATIONS_TABLE} (
                    relation_name, source_id, kind, is_primary, parent_relation, row_count, grain,
                    identifier_columns_json, time_columns_json, measure_columns_json, dimension_columns_json, lineage_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    relation.relation.name,
                    package.source_id,
                    relation.relation.kind,
                    relation.relation.is_primary,
                    relation.relation.parent_relation,
                    relation.relation.row_count,
                    relation.relation.grain,
                    json.dumps(relation.relation.identifier_columns),
                    json.dumps(relation.relation.time_columns),
                    json.dumps(relation.relation.measure_columns),
                    json.dumps(relation.relation.dimension_columns),
                    json.dumps(relation.relation.lineage),
                ],
            )
            column_rows = [
                (
                    package.source_id,
                    relation.relation.name,
                    ordinal,
                    column.name,
                    column.dtype,
                    column.type_family,
                    column.original_name,
                    column.source_path,
                    column.nullable,
                    json.dumps(column.semantic_hints),
                )
                for ordinal, column in enumerate(relation.relation.columns, start=1)
            ]
            if column_rows:
                conn.executemany(
                    f"""
                    INSERT INTO {_COLUMNS_TABLE} (
                        source_id, relation_name, ordinal, column_name, dtype, type_family,
                        original_name, source_path, nullable, semantic_hints_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    column_rows,
                )

        conn.execute(f'DELETE FROM {_LINKS_TABLE} WHERE left_source_id = ? OR right_source_id = ?', [package.source_id, package.source_id])
        for link in package.links:
            conn.execute(
                f"""
                INSERT INTO {_LINKS_TABLE} (
                    link_id, left_source_id, left_relation_name, right_source_id, right_relation_name,
                    link_type, is_explicit, join_keys_json, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    _short_id("link"),
                    link.left_source_id,
                    link.left_relation_name,
                    link.right_source_id,
                    link.right_relation_name,
                    link.link_type,
                    link.is_explicit,
                    json.dumps(link.join_keys),
                    json.dumps(link.metadata),
                ],
            )

        primary = next(item for item in package.relations if item.relation.is_primary)
        row_count = primary.relation.row_count
        content_hash = sha256(package.raw_payload or b"").hexdigest()
        raw_payload = None if package.source_kind == "upload" else package.raw_payload
        conn.execute(f'DELETE FROM {_SOURCES_TABLE} WHERE source_id = ?', [package.source_id])
        conn.execute(
            f"""
            INSERT INTO {_SOURCES_TABLE} (
                source_id, source_name, source_slug, source_kind, source_format, origin, file_name, file_type,
                size_bytes, created_at, content_hash, primary_relation_name, relation_count, row_count, status, raw_payload, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                package.source_id,
                package.source_name,
                package.source_slug,
                package.source_kind,
                package.source_format,
                package.origin,
                package.file_name,
                package.file_type,
                package.size_bytes,
                created_at,
                content_hash,
                package.primary_relation_name,
                len(package.relations),
                row_count,
                "verified",
                raw_payload,
                json.dumps(package.metadata),
            ],
        )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise


def _build_primary_relation_name(source_slug: str, source_id: str) -> str:
    return f"{source_slug}_{source_id.split('_')[-1]}"


def _build_child_relation_name(primary_relation_name: str, path_segments: tuple[str, ...]) -> str:
    suffix = "__".join(_safe_identifier(segment) for segment in path_segments)
    return f"{primary_relation_name}__{suffix}"


def _ingest_csv_source(filename: str, content: bytes, source_id: str | None = None) -> SourcePackage:
    safe_name = Path(filename or "upload.csv").name
    frame = _ensure_record_id(_rename_system_columns(_read_uploaded_frame(safe_name, content)))
    frame = _coerce_frame_types(frame)
    source_id = source_id or _short_id("source")
    source_slug = _slugify(Path(safe_name).stem)
    relation_name = _build_primary_relation_name(source_slug, source_id)
    column_paths = {
        str(column): {
            "original_name": str(column),
            "source_path": str(column),
        }
        for column in frame.columns
    }
    relation = _schema_relation_for_frame(
        relation_name=relation_name,
        source_id=source_id,
        source_name=safe_name,
        frame=frame,
        kind="table",
        is_primary=True,
        parent_relation=None,
        join_keys=[],
        lineage={"format": "csv", "json_path": "$"},
        column_paths=column_paths,
    )
    return SourcePackage(
        source_id=source_id,
        source_name=safe_name,
        source_slug=source_slug,
        source_kind="upload",
        source_format="csv",
        origin="Workspace upload",
        file_name=safe_name,
        file_type=_derive_file_type(safe_name, "csv"),
        size_bytes=len(content),
        raw_payload=content,
        relations=[RelationPackage(relation=relation, frame=frame)],
    )


def _ingest_json_source(filename: str, content: bytes, source_id: str | None = None) -> SourcePackage:
    safe_name = Path(filename or "upload.json").name
    try:
        payload = json.loads(content.decode("utf-8"))
    except Exception as exc:  # pragma: no cover - json errors vary
        raise ValueError(f"Could not parse {safe_name} as JSON.") from exc

    if isinstance(payload, dict):
        records = [payload]
    elif isinstance(payload, list) and all(isinstance(item, dict) for item in payload):
        records = payload
    elif isinstance(payload, list) and not payload:
        records = []
    else:
        raise ValueError("JSON uploads must contain a top-level object or an array of objects.")

    source_id = source_id or _short_id("source")
    source_slug = _slugify(Path(safe_name).stem)
    primary_relation_name = _build_primary_relation_name(source_slug, source_id)

    relation_rows: dict[tuple[str, ...], list[dict[str, Any]]] = {(): []}
    relation_column_paths: dict[tuple[str, ...], dict[str, dict[str, str]]] = {(): {"record_id": {"original_name": "record_id", "source_path": "$.record_id"}}}
    relation_parents: dict[tuple[str, ...], str | None] = {(): None}
    relation_links: list[SourceLinkPackage] = []

    def remember_column(path_key: tuple[str, ...], column_name: str, original_name: str, source_path: str) -> None:
        relation_column_paths.setdefault(path_key, {})
        relation_column_paths[path_key][column_name] = {"original_name": original_name, "source_path": source_path}

    def walk_object(
        obj: dict[str, Any],
        *,
        path_key: tuple[str, ...],
        row: dict[str, Any],
        record_id: str,
        full_path: tuple[str, ...],
    ) -> None:
        for raw_key, value in obj.items():
            safe_key = _safe_identifier(str(raw_key))
            full_column_path = full_path + (str(raw_key),)
            if safe_key in _SYSTEM_COLUMNS:
                safe_key = f"{safe_key}_value"
            if isinstance(value, dict):
                walk_object(
                    value,
                    path_key=path_key,
                    row=row,
                    record_id=record_id,
                    full_path=full_column_path,
                )
                continue
            if isinstance(value, list):
                handle_array(
                    value,
                    parent_relation_path=path_key,
                    parent_relation_name=primary_relation_name if not path_key else _build_child_relation_name(primary_relation_name, path_key),
                    parent_record_id=record_id,
                    array_path=path_key + (safe_key,),
                    full_path=full_column_path,
                )
                continue

            column_name = "__".join(_safe_identifier(part) for part in full_column_path[len(path_key) :])
            if column_name in _SYSTEM_COLUMNS:
                column_name = f"{column_name}_value"
            row[column_name] = _normalize_scalar(value)
            remember_column(path_key, column_name, str(raw_key), ".".join(full_column_path))

    def handle_array(
        values: list[Any],
        *,
        parent_relation_path: tuple[str, ...],
        parent_relation_name: str,
        parent_record_id: str,
        array_path: tuple[str, ...],
        full_path: tuple[str, ...],
    ) -> None:
        relation_rows.setdefault(array_path, [])
        relation_column_paths.setdefault(
            array_path,
            {
                "record_id": {"original_name": "record_id", "source_path": ".".join(full_path) + ".record_id"},
                "parent_record_id": {"original_name": "parent_record_id", "source_path": ".".join(full_path) + ".parent_record_id"},
                "ordinal": {"original_name": "ordinal", "source_path": ".".join(full_path) + ".ordinal"},
            },
        )
        relation_parents[array_path] = parent_relation_name
        relation_name = _build_child_relation_name(primary_relation_name, array_path)
        if not any(link.right_relation_name == relation_name for link in relation_links):
            relation_links.append(
                SourceLinkPackage(
                    left_source_id=source_id,
                    left_relation_name=parent_relation_name,
                    right_source_id=source_id,
                    right_relation_name=relation_name,
                    join_keys=[{"left_column": "record_id", "right_column": "parent_record_id"}],
                    link_type="parent_child",
                    is_explicit=False,
                    metadata={"json_path": ".".join(full_path), "parent_relation_path": ".".join(parent_relation_path)},
                )
            )
        for index, item in enumerate(values):
            child_record_id = f"{parent_record_id}__{_safe_identifier(array_path[-1])}_{index + 1}"
            child_row = {
                "record_id": child_record_id,
                "parent_record_id": parent_record_id,
                "ordinal": index,
            }
            if isinstance(item, dict):
                walk_object(item, path_key=array_path, row=child_row, record_id=child_record_id, full_path=full_path)
            elif isinstance(item, list):
                handle_array(
                    item,
                    parent_relation_path=array_path,
                    parent_relation_name=relation_name,
                    parent_record_id=child_record_id,
                    array_path=array_path + ("value",),
                    full_path=full_path + ("value",),
                )
            else:
                child_row["value"] = _normalize_scalar(item)
                remember_column(array_path, "value", "value", ".".join(full_path))
            relation_rows[array_path].append(child_row)

    for index, item in enumerate(records, start=1):
        if not isinstance(item, dict):
            raise ValueError("JSON uploads must contain objects at the top level.")
        row = {"record_id": f"record_{index}"}
        walk_object(item, path_key=(), row=row, record_id=row["record_id"], full_path=())
        relation_rows[()].append(row)

    primary_frame = pd.DataFrame(relation_rows[()])
    if "record_id" not in primary_frame.columns:
        primary_frame["record_id"] = pd.Series(dtype="string")
    primary_frame = _coerce_frame_types(primary_frame)
    relations: list[RelationPackage] = [
        RelationPackage(
            relation=_schema_relation_for_frame(
                relation_name=primary_relation_name,
                source_id=source_id,
                source_name=safe_name,
                frame=primary_frame,
                kind="table",
                is_primary=True,
                parent_relation=None,
                join_keys=[],
                lineage={"format": "json", "json_path": "$"},
                column_paths=relation_column_paths.get((), {}),
            ),
            frame=primary_frame,
        )
    ]

    for relation_path in sorted(key for key in relation_rows if key):
        relation_name = _build_child_relation_name(primary_relation_name, relation_path)
        frame = _coerce_frame_types(pd.DataFrame(relation_rows[relation_path]))
        join_keys = [
            SchemaJoinKey(
                target_relation=relation_parents[relation_path] or primary_relation_name,
                source_column="parent_record_id",
                target_column="record_id",
                link_type="parent_child",
            )
        ]
        relations.append(
            RelationPackage(
                relation=_schema_relation_for_frame(
                    relation_name=relation_name,
                    source_id=source_id,
                    source_name=safe_name,
                    frame=frame,
                    kind="table",
                    is_primary=False,
                    parent_relation=relation_parents[relation_path],
                    join_keys=join_keys,
                    lineage={"format": "json", "json_path": ".".join(relation_path)},
                    column_paths=relation_column_paths.get(relation_path, {}),
                ),
                frame=frame,
            )
        )

    return SourcePackage(
        source_id=source_id,
        source_name=safe_name,
        source_slug=source_slug,
        source_kind="upload",
        source_format="json",
        origin="Workspace upload",
        file_name=safe_name,
        file_type=_derive_file_type(safe_name, "json"),
        size_bytes=len(content),
        raw_payload=content,
        relations=relations,
        links=relation_links,
    )


def ensure_builtin_sources() -> None:
    """Backward-compatible no-op now that uploads are the only runtime data sources."""


def ingest_source(filename: str, content: bytes, *, source_id: str | None = None) -> UploadedAsset:
    """Persist a CSV/JSON upload into the registry and return its UI summary."""

    safe_name = Path(filename or "upload.csv").name
    suffix = Path(safe_name).suffix.lower()
    if suffix == ".json":
        package = _ingest_json_source(safe_name, content, source_id=source_id)
    elif suffix == ".csv":
        package = _ingest_csv_source(safe_name, content, source_id=source_id)
    else:
        raise ValueError("Only CSV and JSON uploads are currently supported.")
    conn = _connect_registry(read_only=False)
    try:
        _persist_source_package(conn, package)
    finally:
        conn.close()
    from app.data.semantic_model import clear_semantic_context_cache

    clear_semantic_context_cache()
    return _build_uploaded_asset(package)


def delete_source(source_id: str) -> None:
    """Remove one uploaded source and all of its relations from the registry."""

    conn = _connect_registry(read_only=False)
    try:
        relation_names = [
            row[0]
            for row in conn.execute(
                f"SELECT relation_name FROM {_RELATIONS_TABLE} WHERE source_id = ?",
                [source_id],
            ).fetchall()
        ]
        conn.execute("BEGIN TRANSACTION")
        try:
            conn.execute(f"DELETE FROM {_COLUMNS_TABLE} WHERE source_id = ?", [source_id])
            conn.execute(f"DELETE FROM {_LINKS_TABLE} WHERE left_source_id = ? OR right_source_id = ?", [source_id, source_id])
            conn.execute(f"DELETE FROM {_RELATIONS_TABLE} WHERE source_id = ?", [source_id])
            conn.execute(f"DELETE FROM {_SOURCES_TABLE} WHERE source_id = ?", [source_id])
            for relation_name in relation_names:
                conn.execute(f'DROP TABLE IF EXISTS "{relation_name}"')
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
    finally:
        conn.close()
    from app.data.semantic_model import clear_semantic_context_cache

    clear_semantic_context_cache()


def create_source_link(
    left_relation_name: str,
    left_column: str,
    right_relation_name: str,
    right_column: str,
) -> None:
    """Create an explicit registry join path between two existing relations."""

    conn = _connect_registry(read_only=False)
    try:
        rows = conn.execute(
            f"""
            SELECT relation_name, source_id
            FROM {_RELATIONS_TABLE}
            WHERE relation_name IN (?, ?)
            """,
            [left_relation_name, right_relation_name],
        ).fetchall()
        relation_to_source = {row[0]: row[1] for row in rows}
        if left_relation_name not in relation_to_source or right_relation_name not in relation_to_source:
            raise ValueError("Both relations must exist before creating an explicit source link.")
        conn.execute(
            f"""
            INSERT INTO {_LINKS_TABLE} (
                link_id, left_source_id, left_relation_name, right_source_id, right_relation_name,
                link_type, is_explicit, join_keys_json, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                _short_id("link"),
                relation_to_source[left_relation_name],
                left_relation_name,
                relation_to_source[right_relation_name],
                right_relation_name,
                "explicit",
                True,
                json.dumps([{"left_column": left_column, "right_column": right_column}]),
                json.dumps({}),
            ],
        )
    finally:
        conn.close()
    from app.data.semantic_model import clear_semantic_context_cache

    clear_semantic_context_cache()


def _load_link_map(conn: duckdb.DuckDBPyConnection, source_ids: list[str] | None = None) -> dict[str, list[SchemaJoinKey]]:
    filter_sql, params = _link_filter_sql(source_ids)
    rows = conn.execute(
        f"""
        SELECT left_source_id, left_relation_name, right_source_id, right_relation_name, link_type, join_keys_json
        FROM {_LINKS_TABLE}
        {filter_sql}
        """,
        params,
    ).fetchall()
    link_map: dict[str, list[SchemaJoinKey]] = {}
    for row in rows:
        _, left_relation_name, _, right_relation_name, link_type, join_keys_json = row
        join_rows = json.loads(join_keys_json or "[]")
        for join_row in join_rows:
            left_key = SchemaJoinKey(
                target_relation=right_relation_name,
                source_column=join_row["left_column"],
                target_column=join_row["right_column"],
                link_type="parent_child" if link_type == "parent_child" else "explicit",
            )
            right_key = SchemaJoinKey(
                target_relation=left_relation_name,
                source_column=join_row["right_column"],
                target_column=join_row["left_column"],
                link_type="parent_child" if link_type == "parent_child" else "explicit",
            )
            link_map.setdefault(left_relation_name, []).append(left_key)
            link_map.setdefault(right_relation_name, []).append(right_key)
    return link_map


def get_schema_manifest(source_ids: list[str] | None = None) -> dict[str, Any]:
    """Return the normalized schema manifest for the requested scope."""

    conn = _connect_registry(read_only=True)
    try:
        filter_sql, params = _source_filter_sql(source_ids)
        relation_rows = conn.execute(
            f"""
            SELECT relation_name, source_id, kind, is_primary, parent_relation, row_count, grain,
                   identifier_columns_json, time_columns_json, measure_columns_json, dimension_columns_json, lineage_json
            FROM {_RELATIONS_TABLE}
            {filter_sql}
            ORDER BY source_id, is_primary DESC, relation_name
            """,
            params,
        ).fetchall()
        source_names = {
            row[0]: row[1]
            for row in conn.execute(
                f"SELECT source_id, source_name FROM {_SOURCES_TABLE}{filter_sql}",
                params,
            ).fetchall()
        }
        link_map = _load_link_map(conn, source_ids)
        relations: list[SchemaRelation] = []
        for row in relation_rows:
            relation_name, source_id, kind, is_primary, parent_relation, row_count, grain, identifier_columns_json, time_columns_json, measure_columns_json, dimension_columns_json, lineage_json = row
            column_rows = conn.execute(
                f"""
                SELECT column_name, dtype, type_family, original_name, source_path, nullable, semantic_hints_json
                FROM {_COLUMNS_TABLE}
                WHERE relation_name = ?
                ORDER BY ordinal
                """,
                [relation_name],
            ).fetchall()
            columns = [
                SchemaColumn(
                    name=column_name,
                    dtype=dtype,
                    type_family=type_family,
                    original_name=original_name or column_name,
                    source_path=source_path or column_name,
                    nullable=bool(nullable),
                    semantic_hints=json.loads(semantic_hints_json or "[]"),
                )
                for column_name, dtype, type_family, original_name, source_path, nullable, semantic_hints_json in column_rows
            ]
            relation = SchemaRelation(
                name=relation_name,
                kind=kind,
                source_id=source_id,
                source_name=source_names.get(source_id, source_id),
                is_primary=bool(is_primary),
                parent_relation=parent_relation,
                row_count=int(row_count),
                grain=grain or "",
                identifier_columns=json.loads(identifier_columns_json or "[]"),
                time_columns=json.loads(time_columns_json or "[]"),
                measure_columns=json.loads(measure_columns_json or "[]"),
                dimension_columns=json.loads(dimension_columns_json or "[]"),
                join_keys=link_map.get(relation_name, []),
                lineage=json.loads(lineage_json or "{}"),
                columns=columns,
                semantic_mappings=_build_semantic_mappings(columns),
            )
            relations.append(relation)

        manifest = SchemaManifest(
            reference_date="",
            source="source_registry",
            dialect="duckdb",
            relations=relations,
            views=[
                {
                    "name": relation.name,
                    "source_id": relation.source_id,
                    "source_name": relation.source_name,
                    "row_count": relation.row_count,
                    "is_primary": relation.is_primary,
                    "columns": [{"name": column.name, "dtype": column.dtype} for column in relation.columns],
                }
                for relation in relations
            ],
        )
        return manifest.model_dump()
    finally:
        conn.close()


def load_relation_frames(source_ids: list[str] | None = None) -> dict[str, pd.DataFrame]:
    """Load materialized relation tables for the requested scope."""

    conn = _connect_registry(read_only=True)
    try:
        filter_sql, params = _source_filter_sql(source_ids)
        names = [
            row[0]
            for row in conn.execute(
                f"SELECT relation_name FROM {_RELATIONS_TABLE}{filter_sql} ORDER BY relation_name",
                params,
            ).fetchall()
        ]
        return {name: conn.execute(f'SELECT * FROM "{name}"').fetchdf() for name in names}
    finally:
        conn.close()


def get_registered_relation_names(source_ids: list[str] | None = None) -> list[str]:
    """Return visible relation names for the requested scope."""

    conn = _connect_registry(read_only=True)
    try:
        filter_sql, params = _source_filter_sql(source_ids)
        return [
            row[0]
            for row in conn.execute(
                f"SELECT relation_name FROM {_RELATIONS_TABLE}{filter_sql} ORDER BY relation_name",
                params,
            ).fetchall()
        ]
    finally:
        conn.close()


def get_upload_source_ids(source_ids: list[str] | None = None) -> list[str]:
    """Return matching uploaded source ids for the provided ids."""

    if not source_ids:
        return []
    conn = _connect_registry(read_only=False)
    try:
        placeholders = ", ".join(["?"] * len(source_ids))
        rows = conn.execute(
            f"""
            SELECT source_id
            FROM {_SOURCES_TABLE}
            WHERE source_kind = 'upload' AND source_id IN ({placeholders})
            ORDER BY source_id
            """,
            list(dict.fromkeys(source_ids)),
        ).fetchall()
        return [row[0] for row in rows]
    finally:
        conn.close()
