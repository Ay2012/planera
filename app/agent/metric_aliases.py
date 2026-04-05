"""Canonical metric alias helpers shared by planner and executor."""

from __future__ import annotations

import re

_CANONICAL_METRIC_ALIASES = {
    "avg_pipeline_velocity": "avg_pipeline_velocity_days",
}


def canonical_metric_alias(name: str) -> str:
    """Return the canonical metric alias for a planned/validated metric column."""

    return _CANONICAL_METRIC_ALIASES.get(name, name)


def canonical_metric_aliases(names: list[str]) -> list[str]:
    """Canonicalize a list of metric aliases while preserving order."""

    seen: set[str] = set()
    result: list[str] = []
    for name in names:
        canonical = canonical_metric_alias(name)
        if canonical in seen:
            continue
        seen.add(canonical)
        result.append(canonical)
    return result


def canonicalize_sql_metric_aliases(query: str) -> str:
    """Rewrite known metric aliases in SQL to their canonical names."""

    rewritten = query
    for alias, canonical in _CANONICAL_METRIC_ALIASES.items():
        rewritten = re.sub(
            rf"(?i)\bAS\s+{re.escape(alias)}\b",
            f"AS {canonical}",
            rewritten,
        )
    return rewritten

