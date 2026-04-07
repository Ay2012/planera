"""Compatibility tests for execution-phase scaffolding."""

from __future__ import annotations

import pytest

from app.agent.executor import execute_plan, execute_single_plan_step
from app.agent.state import create_initial_state


def test_create_initial_state_sets_minimal_defaults() -> None:
    state = create_initial_state("Compare revenue by segment", ["source_123"])

    assert state["query"] == "Compare revenue by segment"
    assert state["source_ids"] == ["source_123"]
    assert state["compiled_plan"] is None
    assert state["analysis"] == ""
    assert state["executed_steps"] == []
    assert state["errors"] == []


def test_execute_plan_stub_raises_not_implemented() -> None:
    with pytest.raises(NotImplementedError, match="Plan execution"):
        execute_plan(create_initial_state("Run query"), {"plan": []})


def test_execute_single_plan_step_stub_raises_not_implemented() -> None:
    with pytest.raises(NotImplementedError, match="Single-step plan execution"):
        execute_single_plan_step(create_initial_state("Run step"), {"id": 1, "query": "SELECT 1"}, attempt=2)
