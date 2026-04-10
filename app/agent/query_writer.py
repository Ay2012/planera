"""Query-writer entrypoints for the staged analytics runtime implementation."""

from __future__ import annotations

from typing import Any

from app.agent._compat import raise_not_implemented
from app.llm import get_llm_client


def write_step_query(state: dict[str, Any]) -> dict[str, Any]:
    """Generate one SQL query for the current workflow step."""

    raise_not_implemented("Query writer runtime")


__all__ = ["get_llm_client", "write_step_query"]
