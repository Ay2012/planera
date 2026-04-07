"""Thin planner wrapper and compatibility import tests."""

from __future__ import annotations

import importlib

import pytest

from app.agent.analysis import get_llm_client, run_analysis_narrative
from app.agent.graph import run_analysis
from app.agent.planner import build_planner_input
from app.schemas import PlannerInput


def test_build_planner_input_delegates_to_data_layer(monkeypatch) -> None:
    expected = PlannerInput(user_query="Hello", execution_dialect="duckdb", sources=[], relationships=[])
    captured: dict[str, object] = {}

    def fake_builder(query: str, source_ids=None):
        captured["query"] = query
        captured["source_ids"] = source_ids
        return expected

    monkeypatch.setattr("app.agent.planner._build_planner_input", fake_builder)

    result = build_planner_input("Hello", ["source_1"])

    assert result == expected
    assert captured == {"query": "Hello", "source_ids": ["source_1"]}


def test_analysis_runtime_stubs_raise_not_implemented() -> None:
    with pytest.raises(NotImplementedError, match="Analysis LLM access"):
        get_llm_client()

    with pytest.raises(NotImplementedError, match="Narrative analysis runtime"):
        run_analysis_narrative({})

    with pytest.raises(NotImplementedError, match="End-to-end analysis graph"):
        run_analysis("Summarize this upload", source_ids=["source_1"])


def test_legacy_agent_modules_remain_importable() -> None:
    for module_name in (
        "app.agent.metric_aliases",
        "app.agent.recommender",
        "app.agent.reviewer",
        "app.agent.synthesizer",
        "app.agent.verifier",
    ):
        assert importlib.import_module(module_name).__name__ == module_name
