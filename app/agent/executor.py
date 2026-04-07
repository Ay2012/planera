"""Compatibility executor stubs for the planner-input phase."""

from __future__ import annotations

from typing import Any

from app.agent._compat import raise_not_implemented


def execute_plan(state: dict[str, Any], compiled_plan: dict[str, Any]) -> dict[str, Any]:
    """Compatibility stub for compiled-plan execution."""

    raise_not_implemented("Plan execution")


def execute_single_plan_step(state: dict[str, Any], step: dict[str, Any], *, attempt: int = 1) -> dict[str, Any]:
    """Compatibility stub for single-step execution."""

    raise_not_implemented("Single-step plan execution")
