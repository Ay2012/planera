"""Compatibility analysis stubs for the planner-input phase."""

from __future__ import annotations

from typing import Any

from app.agent._compat import raise_not_implemented


def get_llm_client() -> Any:
    """Compatibility stub for the historical analysis runtime."""

    raise_not_implemented("Analysis LLM access")


def run_analysis_narrative(state: dict[str, Any]) -> dict[str, Any]:
    """Compatibility stub for narrative rendering."""

    raise_not_implemented("Narrative analysis runtime")
