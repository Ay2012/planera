"""Compatibility tests for deferred analysis-grounding helpers."""

from __future__ import annotations

import pytest

from app.agent.analysis_grounding import build_analysis_evidence, build_approved_claims, validate_rendered_analysis


def test_build_analysis_evidence_stub_raises_not_implemented() -> None:
    with pytest.raises(NotImplementedError, match="Analysis evidence construction"):
        build_analysis_evidence({})


def test_build_approved_claims_stub_raises_not_implemented() -> None:
    with pytest.raises(NotImplementedError, match="Approved-claim construction"):
        build_approved_claims({})


def test_validate_rendered_analysis_stub_raises_not_implemented() -> None:
    with pytest.raises(NotImplementedError, match="Rendered analysis validation"):
        validate_rendered_analysis({}, [], expected_status="answered")
