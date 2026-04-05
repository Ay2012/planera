"""LLM-driven compiled multi-step planner and repair."""

from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from pydantic import ValidationError

from app.agent.executor import preflight_compiled_plan
from app.agent.metric_aliases import canonical_metric_alias, canonical_metric_aliases, canonicalize_sql_metric_aliases
from app.agent.state import AnalysisState
from app.llm import get_llm_client
from app.prompts import render_prompt
from app.schemas import CompiledPlan, RepairDecision, StepExpectation
from app.utils.logging import get_logger

logger = get_logger(__name__)

_COMPILED_PLANNER_ATTEMPTS = 3
_MAX_PROMPT_RELATIONS = 4
_MAX_COLUMNS_PER_RELATION = 18
_PREMISE_TERMS = ("drop", "decline", "decrease", "increase", "improve", "growth", "faster", "slower")


def _canonicalize_step_contract(step: Any, dataset_context: dict[str, Any]) -> Any:
    """Normalize metric aliases in a compiled or repaired step."""

    step.query = canonicalize_sql_metric_aliases(step.query, dataset_context)
    step.expectation.expected_metric_columns = canonical_metric_aliases(step.expectation.expected_metric_columns, dataset_context)
    return step


def _canonicalize_plan_contract(parsed: CompiledPlan, dataset_context: dict[str, Any]) -> CompiledPlan:
    """Normalize metric aliases in the planner output before validation/execution."""

    parsed.metric = canonical_metric_alias(parsed.metric, dataset_context)
    parsed.plan = [_canonicalize_step_contract(step, dataset_context) for step in parsed.plan]
    return parsed


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
    column_terms = _field_terms(column.get("name", ""))
    for hint in column.get("semantic_hints") or []:
        column_terms.update(_field_terms(hint))

    overlap = len(column_terms & question_terms)
    score = overlap * 3
    if column.get("name", "").lower() in question_terms:
        score += 4
    if column.get("name") in {"period", "current_period", "previous_period"}:
        score += 2
    return score


def _relation_relevance_score(relation: dict[str, Any], question_terms: set[str]) -> int:
    score = len(_field_terms(relation.get("name", ""), relation.get("grain", "")) & question_terms) * 4
    score += sum(_column_relevance_score(column, question_terms) for column in relation.get("columns") or [])
    for mapping in relation.get("semantic_mappings") or []:
        score += len(_field_terms(mapping.get("concept", "")) & question_terms) * 5
    return score


def _relation_join_keys(dataset_context: dict[str, Any], relation_name: str) -> set[str]:
    join_keys: set[str] = set()
    for relationship in dataset_context.get("relationships") or []:
        if relationship.get("left_relation") == relation_name:
            join_keys.update(relationship.get("left_on") or [])
        if relationship.get("right_relation") == relation_name:
            join_keys.update(relationship.get("right_on") or [])
    return join_keys


def _mapped_columns_for_question(relation: dict[str, Any], question_terms: set[str]) -> set[str]:
    columns: set[str] = set()
    for mapping in relation.get("semantic_mappings") or []:
        mapping_terms = _field_terms(mapping.get("concept", ""))
        if mapping_terms & question_terms:
            columns.update(mapping.get("columns") or [])
    return columns


def _protected_column_names(relation: dict[str, Any], dataset_context: dict[str, Any], question_terms: set[str]) -> set[str]:
    protected = set(relation.get("identifier_columns") or [])
    protected.update(relation.get("time_columns") or [])
    protected.update(relation.get("measure_columns") or [])
    protected.update(_relation_join_keys(dataset_context, relation.get("name", "")))
    protected.update(_mapped_columns_for_question(relation, question_terms))
    return protected


def _trim_relation_for_prompt(
    relation: dict[str, Any],
    question_terms: set[str],
    dataset_context: dict[str, Any],
) -> dict[str, Any]:
    trimmed = deepcopy(relation)
    columns = list(trimmed.get("columns") or [])
    if len(columns) <= _MAX_COLUMNS_PER_RELATION:
        return trimmed

    protected_names = _protected_column_names(trimmed, dataset_context, question_terms)

    ranked = sorted(
        columns,
        key=lambda column: (
            column.get("name") in protected_names,
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
        if len(selected) >= _MAX_COLUMNS_PER_RELATION and name not in protected_names:
            continue
        selected.append(column)
        selected_names.add(name)
        if len(selected) >= _MAX_COLUMNS_PER_RELATION and protected_names.issubset(selected_names):
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
            "relationships": dataset_context.get("relationships") or [],
        }

    question_terms = _query_terms(question)
    ranked_relations = sorted(relations, key=lambda relation: _relation_relevance_score(relation, question_terms), reverse=True)
    selected = ranked_relations[:_MAX_PROMPT_RELATIONS]
    selected_names = {relation["name"] for relation in selected}
    return {
        "reference_date": dataset_context.get("reference_date", ""),
        "source": dataset_context.get("source", ""),
        "dialect": dataset_context.get("dialect", ""),
        "relations": [_trim_relation_for_prompt(relation, question_terms, dataset_context) for relation in selected],
        "relationships": [
            relationship
            for relationship in (dataset_context.get("relationships") or [])
            if relationship.get("left_relation") in selected_names and relationship.get("right_relation") in selected_names
        ],
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


def _validate_compiled_plan_semantics(parsed: CompiledPlan, query: str) -> str | None:
    steps = parsed.plan
    if not steps:
        return "The plan must contain at least one step."

    first_expectation = steps[0].expectation
    if first_expectation.step_category != "premise_check":
        return "Step 1 must be a premise_check step."
    if first_expectation.comparison_type != "period_comparison":
        return "Step 1 must verify the primary comparison with a period_comparison step."
    if not first_expectation.expected_metric_columns:
        return "Step 1 must declare expected metric columns."
    if not first_expectation.expected_period_column or not first_expectation.requires_distinct_periods:
        return "Step 1 must declare a period column and require distinct periods."
    if not parsed.metric_direction.strip():
        return "Premise-check plans must declare metric_direction."

    step_ids = {step.id for step in steps}
    for index, step in enumerate(steps, start=1):
        expectation = step.expectation
        if index > 1 and expectation.step_category == "premise_check":
            return "Only the first step may be a premise_check step."
        if expectation.comparison_type == "grouped_breakdown" and not expectation.expected_grouping_columns:
            return f"Step {step.id} must declare expected grouping columns for a grouped_breakdown."
        if expectation.requires_distinct_periods and not expectation.expected_period_column:
            return f"Step {step.id} must declare a period column when distinct periods are required."
        if expectation.preserve_population_from_step_id is not None and expectation.preserve_population_from_step_id not in step_ids:
            return f"Step {step.id} references an unknown preserve_population_from_step_id."

    if any(term in query.lower() for term in _PREMISE_TERMS):
        later_premise_like = [
            step.id
            for step in steps[1:]
            if step.expectation.comparison_type == "period_comparison" and not step.expectation.expected_grouping_columns
        ]
        if later_premise_like:
            return f"Only Step 1 should handle the top-level premise comparison, found another comparison-only step: {later_premise_like[0]}."
    return None


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
    failed_step = next((row for row in (plan.get("plan") or []) if str(row.get("id")) == str(failed_step_id)), {})
    return render_prompt(
        "planner_repair.j2",
        query=state["query"],
        failed_step_id=failed_step_id,
        error_message=error_message,
        plan_json=json.dumps(plan, indent=2),
        failed_step_json=json.dumps(failed_step, indent=2),
        failed_step_expectation_json=json.dumps((failed_step or {}).get("expectation", {}), indent=2),
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
            parsed = _canonicalize_plan_contract(parsed, state["dataset_context"])
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

        semantic_error = _validate_compiled_plan_semantics(parsed, state["query"])
        if semantic_error:
            feedback = semantic_error
            logger.warning(
                "Compiled plan semantic validation failed (attempt %s/%s): %s",
                attempt,
                _COMPILED_PLANNER_ATTEMPTS,
                semantic_error,
            )
            if attempt >= _COMPILED_PLANNER_ATTEMPTS:
                raise ValueError(semantic_error)
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
    parsed.updated_step = _canonicalize_step_contract(parsed.updated_step, state["dataset_context"])

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
            original_expectation = StepExpectation.model_validate(row.get("expectation", {}))
            if parsed.updated_step.expectation.model_dump() != original_expectation.model_dump():
                raise ValueError("Repair changed the original step expectation.")
            steps[i] = parsed.updated_step.model_dump()
            replaced = True
            break
    if not replaced:
        raise ValueError(f"Failed step id {failed_step_id} not found in compiled plan.")

    plan["plan"] = steps
    preflight = preflight_compiled_plan(state, plan)
    if preflight["status"] == "failed":
        raise ValueError(
            "Repair did not preserve the original analytical intent: "
            f"{preflight['error']}"
        )
    state["compiled_plan"] = plan
    state["repair_attempted"] = True
    return state
