"""Single LLM pass: interpret executed results into an analytics narrative."""

from __future__ import annotations

import json

from app.agent.state import AnalysisState
from app.llm import get_llm_client


def run_analysis_narrative(state: AnalysisState) -> AnalysisState:
    """Produce markdown-friendly analysis from query, schema context, and step outputs."""

    prompt = f"""
You are a GTM analytics analyst. Explain what the data shows in response to the user's question.

Rules:
- Base conclusions only on the executed steps and their artifacts below. Do not invent numbers.
- If there were no successful steps or data is insufficient, say so clearly.
- Use markdown: short headings, bullets where helpful.
- Return JSON only in this shape:
{{ "analysis": "<markdown string>" }}

User question:
{state["query"]}

Dataset schema (reference):
{json.dumps(state["dataset_context"], indent=2)}

Executed steps (with previews where available):
{json.dumps(state["executed_steps"], indent=2)}
"""
    try:
        result = get_llm_client().generate_json(prompt)
        state["analysis"] = result.get("analysis", "").strip() or "No analysis text was returned."
    except Exception as exc:  # pragma: no cover - defensive
        state["analysis"] = (
            f"The analysis step could not complete ({exc!s}). "
            "Review the executed steps and trace for raw outputs."
        )
    return state
