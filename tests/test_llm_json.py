"""Regression tests for LLM JSON parsing."""

from __future__ import annotations

from app.llm.json_response import parse_llm_json_object


def test_parse_llm_json_allows_literal_newlines_in_strings() -> None:
    """Models often emit multi-line SQL without \\n escapes; strict JSON rejects that."""
    raw = '{"query": "SELECT\n1", "id": 1}'
    out = parse_llm_json_object(raw, source="test")
    assert out["query"] == "SELECT\n1"
    assert out["id"] == 1
