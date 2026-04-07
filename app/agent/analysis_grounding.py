"""Compatibility grounding stubs for the planner-input phase."""

from __future__ import annotations

from app.agent._compat import raise_not_implemented


def build_analysis_evidence(state: dict) -> dict:
    """Compatibility stub for evidence construction."""

    raise_not_implemented("Analysis evidence construction")


def build_approved_claims(evidence: dict) -> tuple[list, str]:
    """Compatibility stub for deterministic claim approval."""

    raise_not_implemented("Approved-claim construction")


def validate_rendered_analysis(response, claims, *, expected_status: str) -> None:
    """Compatibility stub for rendered-analysis validation."""

    raise_not_implemented("Rendered analysis validation")
