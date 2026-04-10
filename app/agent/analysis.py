"""Analyzer entrypoints for the staged analytics runtime implementation."""

from __future__ import annotations

from typing import Any

from app.agent._compat import raise_not_implemented
from app.llm import get_llm_client


def analyze_workflow(state: dict[str, Any]) -> dict[str, Any]:
    """Produce the final analyzer decision for the workflow run."""

    raise_not_implemented("Analyzer runtime")


__all__ = ["analyze_workflow", "get_llm_client"]
