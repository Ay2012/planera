"""Schema-aware metric alias helpers shared by planner and executor."""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

_AGGREGATE_PREFIXES = {"avg", "sum", "count", "min", "max", "median"}
_AGGREGATE_ALIAS_PATTERN = re.compile(
    r"(?i)\b(?P<func>avg|sum|count|min|max|median)\s*\(\s*(?P<expr>[A-Za-z_][A-Za-z0-9_\.\"`]*)\s*\)\s+AS\s+(?P<alias>[A-Za-z_][A-Za-z0-9_]*)"
)


def _normalize_metric_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _strip_identifier_quotes(value: str) -> str:
    return value.strip().strip('"').strip("`")


def _iter_measure_columns(dataset_context: dict[str, Any] | None) -> list[tuple[str, list[str]]]:
    if not dataset_context:
        return []

    measures: list[tuple[str, list[str]]] = []
    for relation in dataset_context.get("relations") or []:
        measure_names = set(relation.get("measure_columns") or [])
        for column in relation.get("columns") or []:
            column_name = column.get("name", "")
            if not column_name or column_name not in measure_names:
                continue
            hints = list(column.get("semantic_hints") or [])
            measures.append((column_name, hints))
    return measures


def _schema_metric_lookup(dataset_context: dict[str, Any] | None) -> dict[str, str]:
    matches: dict[str, set[str]] = defaultdict(set)
    for column_name, hints in _iter_measure_columns(dataset_context):
        matches[_normalize_metric_key(column_name)].add(column_name)
        for hint in hints:
            normalized = _normalize_metric_key(hint)
            if normalized:
                matches[normalized].add(column_name)

    resolved: dict[str, str] = {}
    for normalized, candidates in matches.items():
        if len(candidates) == 1:
            resolved[normalized] = next(iter(candidates))
    return resolved


def resolve_metric_base_name(name: str, dataset_context: dict[str, Any] | None) -> str:
    """Resolve a metric-like identifier to a canonical schema-backed base name when uniquely possible."""

    cleaned = _strip_identifier_quotes(name)
    lookup = _schema_metric_lookup(dataset_context)
    return lookup.get(_normalize_metric_key(cleaned), cleaned)


def canonical_metric_alias(name: str, dataset_context: dict[str, Any] | None = None) -> str:
    """Canonicalize aggregate metric aliases from planner expectations or result columns."""

    cleaned = _strip_identifier_quotes(name)
    match = re.match(rf"^(?P<prefix>{'|'.join(sorted(_AGGREGATE_PREFIXES))})_(?P<base>.+)$", cleaned, flags=re.IGNORECASE)
    if not match:
        return cleaned
    prefix = match.group("prefix").lower()
    base = resolve_metric_base_name(match.group("base"), dataset_context)
    return f"{prefix}_{base}"


def canonical_metric_aliases(names: list[str], dataset_context: dict[str, Any] | None = None) -> list[str]:
    """Canonicalize a list of metric aliases while preserving order."""

    seen: set[str] = set()
    result: list[str] = []
    for name in names:
        canonical = canonical_metric_alias(name, dataset_context)
        if canonical in seen:
            continue
        seen.add(canonical)
        result.append(canonical)
    return result


def canonicalize_sql_metric_aliases(query: str, dataset_context: dict[str, Any] | None = None) -> str:
    """Rewrite aggregate metric aliases in SQL to canonical schema-aware names."""

    def repl(match: re.Match[str]) -> str:
        func = match.group("func")
        expr = match.group("expr")
        base_expr = _strip_identifier_quotes(expr.split(".")[-1])
        canonical_base = resolve_metric_base_name(base_expr, dataset_context)
        canonical_alias = f"{func.lower()}_{canonical_base}"
        return f"{func}({expr}) AS {canonical_alias}"

    return _AGGREGATE_ALIAS_PATTERN.sub(repl, query)

