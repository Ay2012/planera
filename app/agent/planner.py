"""LLM-driven compiled multi-step planner and repair."""

from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from pydantic import ValidationError

from app.agent.executor import preflight_compiled_plan
from app.agent.state import AnalysisState
from app.llm import get_llm_client
from app.prompts import render_prompt
from app.schemas import CompiledPlan, RepairDecision
from app.utils.logging import get_logger

logger = get_logger(__name__)

_COMPILED_PLANNER_ATTEMPTS = 3
_MAX_PROMPT_RELATIONS = 4
_MAX_COLUMNS_PER_RELATION = 18


def _query_terms(question: str) -> set[str]:
    return {token.lower() for token in re.findall(r"[a-zA-Z0-9_]+", question) if len(token) >= 3}


def _field_terms(*values: str) -> set[str]:
    terms: set[str] = set()
    for value in values:
        normalized = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
        for token in re.findall(r"[a-zA-Z0-9]+", normalized.lower().replace("_", " ")):
            if len(token) >= 3:
                terms.add(token)
    return terms


def _column_relevance_score(column: dict[str, Any], question_terms: set[str]) -> int:
    column_terms = _field_terms(
        column.get("name", ""),
        column.get("original_name", ""),
        column.get("source_path", ""),
    )
    for hint in column.get("semantic_hints") or []:
        column_terms.update(_field_terms(hint))

    overlap = len(column_terms & question_terms)
    score = overlap * 3
    if column.get("name", "").lower() in question_terms:
        score += 4
    return score


def _relation_relevance_score(relation: dict[str, Any], question_terms: set[str]) -> int:
    score = len(
        _field_terms(
            relation.get("name", ""),
            relation.get("grain", ""),
            relation.get("source_name", ""),
            json.dumps(relation.get("lineage", {}), default=str),
        )
        & question_terms
    ) * 4
    score += sum(_column_relevance_score(column, question_terms) for column in relation.get("columns") or [])
    for mapping in relation.get("semantic_mappings") or []:
        score += len(_field_terms(mapping.get("concept", "")) & question_terms) * 5
    if relation.get("is_primary"):
        score += 3
    return score


def _trim_relation_for_prompt(relation: dict[str, Any], question_terms: set[str]) -> dict[str, Any]:
    trimmed = deepcopy(relation)
    columns = list(trimmed.get("columns") or [])
    if len(columns) <= _MAX_COLUMNS_PER_RELATION:
        return trimmed

    ranked = sorted(
        columns,
        key=lambda column: (
            _column_relevance_score(column, question_terms),
            column.get("name") in (trimmed.get("identifier_columns") or []),
            column.get("name") in (trimmed.get("time_columns") or []),
        ),
        reverse=True,
    )
    selected: list[dict[str, Any]] = []
    selected_names: set[str] = set()
    for column in ranked:
        name = column.get("name", "")
        if not name or name in selected_names:
            continue
        selected.append(column)
        selected_names.add(name)
        if len(selected) >= _MAX_COLUMNS_PER_RELATION:
            break

    trimmed["columns"] = selected
    trimmed["identifier_columns"] = [name for name in trimmed.get("identifier_columns") or [] if name in selected_names]
    trimmed["time_columns"] = [name for name in trimmed.get("time_columns") or [] if name in selected_names]
    trimmed["measure_columns"] = [name for name in trimmed.get("measure_columns") or [] if name in selected_names]
    trimmed["dimension_columns"] = [name for name in trimmed.get("dimension_columns") or [] if name in selected_names]
    trimmed["semantic_mappings"] = [
        mapping
        for mapping in (trimmed.get("semantic_mappings") or [])
        if any(name in selected_names for name in mapping.get("columns") or [])
    ][:12]
    trimmed["omitted_column_count"] = max(len(columns) - len(selected), 0)
    return trimmed


def _schema_subset_for_question(dataset_context: dict[str, Any], question: str) -> dict[str, Any]:
    relations = list(dataset_context.get("relations") or [])
    if not relations:
        return dataset_context

    total_columns = sum(len(relation.get("columns") or []) for relation in relations)
    if len(relations) <= _MAX_PROMPT_RELATIONS and total_columns <= (_MAX_PROMPT_RELATIONS * _MAX_COLUMNS_PER_RELATION):
        return {
            "reference_date": dataset_context.get("reference_date", ""),
            "source": dataset_context.get("source", ""),
            "dialect": dataset_context.get("dialect", ""),
            "relations": relations,
        }

    question_terms = _query_terms(question)
    ranked_relations = sorted(relations, key=lambda relation: _relation_relevance_score(relation, question_terms), reverse=True)
    selected = ranked_relations[:_MAX_PROMPT_RELATIONS]
    return {
        "reference_date": dataset_context.get("reference_date", ""),
        "source": dataset_context.get("source", ""),
        "dialect": dataset_context.get("dialect", ""),
        "relations": [_trim_relation_for_prompt(relation, question_terms) for relation in selected],
    }


def _relation_names(dataset_context: dict[str, Any]) -> list[str]:
    relations = dataset_context.get("relations") or []
    if relations:
        return [relation["name"] for relation in relations]
    return [view["name"] for view in dataset_context.get("views", [])]


def _planner_preflight_feedback(outcome: dict[str, Any], schema_subset: dict[str, Any]) -> str:
    return (
        "Your previous plan failed SQL preflight validation.\n"
        f"Failed step id: {outcome.get('failed_step_id', '')}\n"
        f"Error: {outcome.get('error', '')}\n"
        f"SQL:\n{outcome.get('query', '').strip()}\n\n"
        "Fix guidance:\n"
        "- Use only exact relation and column names from the schema subset.\n"
        "- Resolve business-language terms through semantic mappings, then use the mapped exact field names in SQL.\n"
        "- Do not invent fields or rename columns.\n"
        "- If the question premise might be wrong, start with an overall comparison before segment-level breakdowns.\n"
        f"- Target SQL dialect: {schema_subset.get('dialect', '') or 'unknown'}.\n"
    )


def _build_compiled_planner_prompt(state: AnalysisState, validation_feedback: str | None = None) -> str:
    schema_subset = _schema_subset_for_question(state["dataset_context"], state["query"])
    relation_names = _relation_names(schema_subset)
    return render_prompt(
        "planner_compiled.j2",
        query=state["query"],
        relation_names_json=json.dumps(relation_names),
        schema_subset_json=json.dumps(schema_subset, indent=2),
        validation_feedback=validation_feedback,
    )


def _build_repair_prompt(state: AnalysisState, failed_step_id: str, error_message: str) -> str:
    plan = state.get("compiled_plan") or {}
    schema_subset = _schema_subset_for_question(state["dataset_context"], state["query"])
    return render_prompt(
        "planner_repair.j2",
        failed_step_id=failed_step_id,
        error_message=error_message,
        plan_json=json.dumps(plan, indent=2),
        schema_subset_json=json.dumps(schema_subset, indent=2),
    )


def plan_compiled_query(state: AnalysisState) -> AnalysisState:
    """Call the LLM to produce a full compiled plan (max 3 SQL steps), with retries on schema errors."""

    client = get_llm_client()
    feedback: str | None = None

    for attempt in range(1, _COMPILED_PLANNER_ATTEMPTS + 1):
        prompt = _build_compiled_planner_prompt(state, validation_feedback=feedback)
        try:
            decision = client.generate_json(prompt, schema=CompiledPlan)
            parsed = decision if isinstance(decision, CompiledPlan) else CompiledPlan.model_validate(decision)
        except (ValidationError, ValueError) as exc:
            feedback = exc.json(indent=2) if isinstance(exc, ValidationError) else str(exc)
            logger.warning(
                "Compiled plan validation failed (attempt %s/%s): %s",
                attempt,
                _COMPILED_PLANNER_ATTEMPTS,
                exc.errors() if isinstance(exc, ValidationError) else str(exc),
            )
            if attempt >= _COMPILED_PLANNER_ATTEMPTS:
                raise
            continue

        preflight = preflight_compiled_plan(state, parsed.model_dump())
        if preflight["status"] == "failed":
            feedback = _planner_preflight_feedback(preflight, _schema_subset_for_question(state["dataset_context"], state["query"]))
            logger.warning(
                "Compiled plan preflight failed (attempt %s/%s): %s",
                attempt,
                _COMPILED_PLANNER_ATTEMPTS,
                preflight["error"],
            )
            if attempt >= _COMPILED_PLANNER_ATTEMPTS:
                raise ValueError(preflight["error"])
            continue

        state["compiled_plan"] = parsed.model_dump()
        state["planner_reasoning"] = parsed.objective
        state["metric"] = parsed.metric
        state["intent"] = "diagnosis"
        state["workflow_status"] = "ready_to_execute"
        return state


def repair_failed_step(state: AnalysisState, failed_step_id: str, error_message: str) -> AnalysisState:
    """Call the LLM once to replace a single failed plan step."""

    raw = get_llm_client().generate_json(
        _build_repair_prompt(state, failed_step_id, error_message),
        schema=RepairDecision,
    )
    parsed = raw if isinstance(raw, RepairDecision) else RepairDecision.model_validate(raw)

    if str(parsed.updated_step.id) != str(failed_step_id):
        raise ValueError(f"Repair returned mismatched step id: expected {failed_step_id}, got {parsed.updated_step.id}")

    plan = state.get("compiled_plan")
    if not plan:
        raise ValueError("No compiled plan to repair.")

    steps = list(plan.get("plan") or [])
    replaced = False
    for i, row in enumerate(steps):
        sid = row.get("id") if isinstance(row, dict) else row["id"]
        if str(sid) == str(failed_step_id):
            steps[i] = parsed.updated_step.model_dump()
            replaced = True
            break
    if not replaced:
        raise ValueError(f"Failed step id {failed_step_id} not found in compiled plan.")

    plan["plan"] = steps
    state["compiled_plan"] = plan
    state["repair_attempted"] = True
    return state
