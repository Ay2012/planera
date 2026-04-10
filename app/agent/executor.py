"""Executor entrypoints for the staged analytics runtime implementation."""

from __future__ import annotations

from typing import Any

from app.agent._compat import raise_not_implemented


def execute_current_step(state: dict[str, Any]) -> dict[str, Any]:
    """Execute the query for the current workflow step."""

    raise_not_implemented("Step execution runtime")


def build_best_effort_state(state: dict[str, Any]) -> dict[str, Any]:
    """Populate the best-effort answer path after retry limits are exhausted."""

    raise_not_implemented("Best-effort execution fallback")
