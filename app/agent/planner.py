"""Planner runtime for the schema-grounded analytics workflow."""

from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from app.data.planner_input import build_planner_input as _build_raw_planner_input
from app.llm import get_llm_client
from app.prompts import render_prompt
from app.schemas import AnalysisPlan, CompactSchemaColumn, CompactSchemaContext, CompactSchemaRelation, PlannerInput


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
        column.get("dtype", ""),
    )
    for hint in column.get("semantic_hints") or []:
        column_terms.update(_field_terms(str(hint)))

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
            column.get("name") in (trimmed.get("measure_columns") or []),
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
    return trimmed


def _coerce_relation(relation: dict[str, Any]) -> CompactSchemaRelation:
    return CompactSchemaRelation(
        name=relation.get("name", ""),
        source_id=relation.get("source_id", ""),
        source_name=relation.get("source_name", ""),
        is_primary=bool(relation.get("is_primary")),
        row_count=int(relation.get("row_count", 0) or 0),
        grain=relation.get("grain", "") or "",
        identifier_columns=list(relation.get("identifier_columns") or []),
        time_columns=list(relation.get("time_columns") or []),
        measure_columns=list(relation.get("measure_columns") or []),
        dimension_columns=list(relation.get("dimension_columns") or []),
        join_keys=list(relation.get("join_keys") or []),
        semantic_mappings=list(relation.get("semantic_mappings") or []),
        columns=[
            CompactSchemaColumn(
                name=column.get("name", ""),
                dtype=column.get("dtype", ""),
                type_family=column.get("type_family", "unknown"),
                nullable=bool(column.get("nullable", True)),
                semantic_hints=list(column.get("semantic_hints") or []),
            )
            for column in (relation.get("columns") or [])
        ],
    )


def _render_plan_prompt(
    *,
    query: str,
    planner_input_json: dict[str, Any] | None = None,
    schema_context_summary: dict[str, Any],
    failure_summary: str = "",
    current_plan: dict[str, Any] | None = None,
) -> str:
    template_name = "planner_replan.j2" if failure_summary else "planner_plan.j2"
    return render_prompt(
        template_name,
        query=query,
        planner_input_json=json.dumps(planner_input_json, indent=2) if planner_input_json else "",
        schema_context_json=json.dumps(schema_context_summary, indent=2),
        failure_summary=failure_summary,
        current_plan_json=json.dumps(current_plan or {}, indent=2),
    )


def _planner_input_for_state(state: dict[str, Any]) -> dict[str, Any] | None:
    existing = state.get("planner_input")
    if isinstance(existing, dict):
        if existing.get("sources") or existing.get("relationships"):
            return existing
        return None

    source_ids = list(state.get("source_ids") or [])
    if not source_ids:
        return None

    try:
        planner_input = _build_raw_planner_input(state["query"], source_ids=source_ids)
    except Exception:
        return None

    payload = planner_input.model_dump()
    if not payload.get("sources") and not payload.get("relationships"):
        return None

    state["planner_input"] = payload
    return payload


def build_compact_schema_context(dataset_context: dict[str, Any], question: str) -> dict[str, Any]:
    """Return a compact schema/context summary for planning prompts."""

    relations = list(dataset_context.get("relations") or [])
    if not relations:
        context = CompactSchemaContext(
            reference_date=dataset_context.get("reference_date", ""),
            source=dataset_context.get("source", ""),
            dialect=dataset_context.get("dialect", ""),
            relations=[],
        )
        return context.model_dump()

    question_terms = _query_terms(question)
    total_columns = sum(len(relation.get("columns") or []) for relation in relations)
    if len(relations) > _MAX_PROMPT_RELATIONS or total_columns > (_MAX_PROMPT_RELATIONS * _MAX_COLUMNS_PER_RELATION):
        ranked_relations = sorted(
            relations,
            key=lambda relation: _relation_relevance_score(relation, question_terms),
            reverse=True,
        )
        selected_relations = ranked_relations[:_MAX_PROMPT_RELATIONS]
    else:
        selected_relations = relations

    context = CompactSchemaContext(
        reference_date=dataset_context.get("reference_date", ""),
        source=dataset_context.get("source", ""),
        dialect=dataset_context.get("dialect", ""),
        relations=[_coerce_relation(_trim_relation_for_prompt(relation, question_terms)) for relation in selected_relations],
    )
    return context.model_dump()


def plan_analysis(state: dict[str, Any]) -> dict[str, Any]:
    """Return the planner-authored full workflow plan."""

    planner_input = _planner_input_for_state(state)
    schema_context_summary = state.get("schema_context_summary") or build_compact_schema_context(
        state.get("dataset_context", {}),
        state["query"],
    )
    state["schema_context_summary"] = schema_context_summary
    prompt = _render_plan_prompt(
        query=state["query"],
        planner_input_json=planner_input,
        schema_context_summary=schema_context_summary,
    )
    result = get_llm_client().generate_json(prompt, schema=AnalysisPlan)
    parsed = result if isinstance(result, AnalysisPlan) else AnalysisPlan.model_validate(result)
    state["current_plan"] = parsed.model_dump()
    state["current_step_index"] = 0
    state["workflow_status"] = "planned"
    return state


def replan_analysis(state: dict[str, Any]) -> dict[str, Any]:
    """Return one revised workflow plan after failure."""

    planner_input = _planner_input_for_state(state)
    schema_context_summary = state.get("schema_context_summary") or build_compact_schema_context(
        state.get("dataset_context", {}),
        state["query"],
    )
    state["schema_context_summary"] = schema_context_summary
    prompt = _render_plan_prompt(
        query=state["query"],
        planner_input_json=planner_input,
        schema_context_summary=schema_context_summary,
        failure_summary=state.get("failure_summary", ""),
        current_plan=state.get("current_plan"),
    )
    result = get_llm_client().generate_json(prompt, schema=AnalysisPlan)
    parsed = result if isinstance(result, AnalysisPlan) else AnalysisPlan.model_validate(result)
    state["current_plan"] = parsed.model_dump()
    state["current_step_index"] = 0
    state["replan_count"] = int(state.get("replan_count", 0) or 0) + 1
    state["workflow_status"] = "replanned"
    return state


def _schema_subset_for_question(dataset_context: dict[str, Any], question: str) -> dict[str, Any]:
    """Compatibility helper kept for schema-focused tests."""

    return build_compact_schema_context(dataset_context, question)


def plan_compiled_query(state: dict[str, Any]) -> dict[str, Any]:
    """Compatibility wrapper retained during the transition away from compiled SQL planning."""

    return plan_analysis(state)


def build_planner_input(query: str, source_ids: list[str] | None = None) -> PlannerInput:
    """Build the raw-schema planner contract for attached uploads."""

    return _build_raw_planner_input(query, source_ids=source_ids)


__all__ = [
    "_schema_subset_for_question",
    "build_compact_schema_context",
    "build_planner_input",
    "get_llm_client",
    "plan_analysis",
    "plan_compiled_query",
    "replan_analysis",
]
