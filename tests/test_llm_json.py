"""Regression tests for structured LLM response validation."""

from __future__ import annotations

import pytest
from pydantic import BaseModel, ConfigDict, ValidationError

from app.llm.gemini import _json_schema_for_gemini_structured_output
from app.llm.json_response import validate_structured_output


class DemoPayload(BaseModel):
    """Small schema used to test structured JSON validation."""

    model_config = ConfigDict(extra="forbid")

    query: str
    id: int


def test_validate_structured_output_accepts_json_string() -> None:
    raw = '{"query": "SELECT\\n1", "id": 1}'
    out = validate_structured_output(raw, schema=DemoPayload, source="test")
    assert out.query == "SELECT\n1"
    assert out.id == 1


def test_validate_structured_output_rejects_extra_keys() -> None:
    with pytest.raises(ValidationError):
        validate_structured_output(
            {"query": "SELECT 1", "id": 1, "unexpected": "nope"},
            schema=DemoPayload,
            source="test",
        )


def _assert_no_additional_properties(obj: object) -> None:
    if isinstance(obj, dict):
        assert "additionalProperties" not in obj
        assert "unevaluatedProperties" not in obj
        for v in obj.values():
            _assert_no_additional_properties(v)
    elif isinstance(obj, list):
        for v in obj:
            _assert_no_additional_properties(v)


def test_json_schema_for_gemini_strips_additional_properties() -> None:
    """Gemini rejects JSON Schema with additionalProperties; our adapter removes them before the API call."""
    s = _json_schema_for_gemini_structured_output(DemoPayload)
    _assert_no_additional_properties(s)
