"""Deterministic evidence, claims, and validation for grounded analysis output."""

from __future__ import annotations

import re
from collections import defaultdict
from difflib import SequenceMatcher
from numbers import Real
from typing import Any

from app.agent.state import AnalysisState
from app.schemas import AnalysisEvidence, AnalysisRenderResponse, ApprovedClaim, EvidenceItem, EvidenceValue, StepExpectation

_NEGATIVE_PREMISE_TERMS = (
    "drop",
    "decline",
    "decrease",
    "down",
    "worse",
    "slower",
    "underperform",
    "fall",
)
_POSITIVE_PREMISE_TERMS = (
    "improve",
    "increase",
    "growth",
    "better",
    "faster",
    "higher",
    "gain",
    "rise",
)
_CURRENT_TERMS = ("current", "latest", "this")
_PREVIOUS_TERMS = ("previous", "prior", "last")
_DEFAULT_METRIC_DIRECTIONS = {
    "pipeline_velocity_days": "lower_is_better",
    "avg_pipeline_velocity_days": "lower_is_better",
}
_BLOCKED_TERMS = (
    "stable",
    "strong",
    "healthy",
    "significant",
    "improving",
    "worsening",
    "improved",
    "worsened",
    "cause",
    "caused",
    "driver",
    "drivers",
    "because",
    "due to",
    "root cause",
)
_GENERIC_PROPER_NOUN_ALLOWLIST = {
    "Summary",
    "Conclusion",
    "Key Findings",
    "Analysis",
    "Evidence",
    "Question",
}
_INTERNAL_LEAK_TERMS = (
    "answer_status must be",
    "review executed steps and trace for raw outputs",
    "validation feedback",
    "validator",
    "traceback",
    "exception",
)


def _is_number(value: Any) -> bool:
    return isinstance(value, Real) and not isinstance(value, bool)


def _format_value(value: Any) -> str:
    if value is None:
        return "null"
    if _is_number(value):
        if float(value).is_integer():
            return str(int(value))
        return f"{float(value):.2f}".rstrip("0").rstrip(".")
    return str(value)


def _infer_premise_hint(question: str) -> str:
    lowered = question.lower()
    if any(term in lowered for term in _NEGATIVE_PREMISE_TERMS):
        return "deterioration"
    if any(term in lowered for term in _POSITIVE_PREMISE_TERMS):
        return "improvement"
    return ""


def _normalize_metric_key(metric: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", metric.lower()).strip("_")


def _as_expectation(value: dict[str, Any] | StepExpectation | None) -> StepExpectation:
    if isinstance(value, StepExpectation):
        return value
    return StepExpectation.model_validate(value or {})


def _candidate_primary_metrics(state: AnalysisState) -> list[str]:
    candidates: list[str] = []
    for candidate in (
        state.get("metric"),
        (state.get("compiled_plan") or {}).get("metric"),
    ):
        if candidate and candidate not in candidates:
            candidates.append(str(candidate))

    plan = state.get("compiled_plan") or {}
    for step in plan.get("plan") or []:
        expectation = _as_expectation(step.get("expectation"))
        if expectation.step_category != "premise_check":
            continue
        for metric in expectation.expected_metric_columns:
            if metric and metric not in candidates:
                candidates.append(metric)
    return candidates


def _resolve_primary_metric(state: AnalysisState, available_metrics: set[str]) -> str:
    candidates = _candidate_primary_metrics(state)
    normalized_available = {_normalize_metric_key(metric): metric for metric in available_metrics}
    for candidate in candidates:
        if candidate in available_metrics:
            return candidate
        normalized = _normalize_metric_key(candidate)
        if normalized in normalized_available:
            return normalized_available[normalized]
        for available_key, available_metric in normalized_available.items():
            if normalized and (normalized in available_key or available_key in normalized):
                return available_metric
    return candidates[0] if candidates else ""


def _resolve_metric_direction(state: AnalysisState, primary_metric: str) -> str:
    plan = state.get("compiled_plan") or {}
    metric_direction = str(plan.get("metric_direction") or "").strip()
    if metric_direction:
        return metric_direction

    normalized = _normalize_metric_key(primary_metric)
    return _DEFAULT_METRIC_DIRECTIONS.get(normalized, "")


def _normalize_period_label(column: str, value: Any, expectation: StepExpectation) -> str:
    if value in (None, ""):
        return ""

    text = str(value).strip()
    lowered_column = column.lower()
    if isinstance(value, bool):
        if "current_period" in lowered_column:
            return "current_week" if value else "previous_week"
        if "previous_period" in lowered_column:
            return "previous_week" if value else "current_week"
        if expectation.expected_period_column and expectation.expected_period_column == column and "period" in lowered_column:
            return "current_period" if value else "previous_period"
        return text.lower()

    lowered_text = text.lower().replace(" ", "_")
    if any(term in lowered_text for term in _CURRENT_TERMS):
        return "current_week"
    if any(term in lowered_text for term in _PREVIOUS_TERMS):
        return "previous_week"
    return lowered_text


def _extract_period_label(
    row: dict[str, Any],
    non_numeric_columns: list[str],
    expectation: StepExpectation,
) -> tuple[str, set[str]]:
    period_columns: set[str] = set()
    if expectation.expected_period_column and expectation.expected_period_column in row:
        period_columns.add(expectation.expected_period_column)
    for column in non_numeric_columns:
        lowered = column.lower()
        if lowered in {"current_period", "previous_period"} or "period" in lowered:
            period_columns.add(column)

    for column in non_numeric_columns:
        if column not in period_columns:
            continue
        label = _normalize_period_label(column, row.get(column), expectation)
        if label and label not in {"false", "true"}:
            return label, period_columns
    return "", period_columns


def _normalized_dimensions(
    row: dict[str, Any],
    non_numeric_columns: list[str],
    period_columns: set[str],
) -> dict[str, str]:
    dimensions: dict[str, str] = {}
    for column in non_numeric_columns:
        if column in period_columns:
            continue
        value = row.get(column)
        if value in (None, ""):
            continue
        dimensions[column] = str(value)
    return dimensions


def _row_label(
    dimensions: dict[str, str],
    period_label: str,
    fallback: str,
) -> str:
    values = list(dimensions.values())
    if values and period_label:
        return f"{' | '.join(values)} | {period_label}"
    if values:
        return values[0] if len(values) == 1 else " | ".join(values)
    if period_label:
        return period_label
    return fallback


def _extract_entities(dimensions: dict[str, str], period_label: str, row_label: str) -> list[str]:
    seen: list[str] = []
    for value in [*dimensions.values(), period_label, row_label]:
        if not value:
            continue
        if value not in seen:
            seen.append(value)
    return seen


def build_analysis_evidence(state: AnalysisState) -> AnalysisEvidence:
    """Build a compact, domain-agnostic evidence packet from executed step previews."""

    items: list[EvidenceItem] = []
    allowed_entities: list[str] = []
    available_metrics: set[str] = set()

    for step in state.get("executed_steps") or []:
        if step.get("status") != "success":
            continue
        if step.get("validation_status") not in (None, "valid", "partial"):
            continue
        expectation = _as_expectation(step.get("expectation"))
        artifact = step.get("artifact") or {}
        preview_rows = artifact.get("preview_rows") or []
        columns = artifact.get("columns") or []
        if not preview_rows or not columns:
            continue

        numeric_columns = [
            column
            for column in columns
            if any(_is_number(row.get(column)) for row in preview_rows)
        ]
        non_numeric_columns = [column for column in columns if column not in numeric_columns]
        available_metrics.update(numeric_columns)

        for index, row in enumerate(preview_rows, start=1):
            period_label, period_columns = _extract_period_label(row, non_numeric_columns, expectation)
            dimensions = _normalized_dimensions(row, non_numeric_columns, period_columns)
            row_label = _row_label(dimensions, period_label, fallback=f"row_{index}")
            entities = _extract_entities(dimensions, period_label, row_label)
            for entity in entities:
                if entity not in allowed_entities:
                    allowed_entities.append(entity)
            values = [EvidenceValue(label=column, value=_format_value(row.get(column))) for column in columns if row.get(column) is not None]
            items.append(
                EvidenceItem(
                    id=f"{artifact.get('alias', step['output_alias'])}_row_{index}",
                    source_alias=artifact.get("alias", step["output_alias"]),
                    source_purpose=step["purpose"],
                    row_label=row_label,
                    step_category=expectation.step_category,
                    comparison_type=expectation.comparison_type,
                    period_label=period_label,
                    dimensions=dimensions,
                    entities=entities,
                    metrics=numeric_columns,
                    values=values,
                )
            )

    primary_metric = _resolve_primary_metric(state, available_metrics)
    return AnalysisEvidence(
        question=state["query"],
        primary_metric=primary_metric,
        metric_direction=_resolve_metric_direction(state, primary_metric),
        premise_hint=_infer_premise_hint(state["query"]),
        items=items,
        allowed_entities=allowed_entities,
    )


def _value_map(item: EvidenceItem) -> dict[str, str]:
    return {value.label: value.value for value in item.values}


def _group_items_by_source(evidence: AnalysisEvidence) -> dict[str, list[EvidenceItem]]:
    grouped: dict[str, list[EvidenceItem]] = defaultdict(list)
    for item in evidence.items:
        grouped[item.source_alias].append(item)
    return grouped


def _sort_period_pair(items: list[EvidenceItem]) -> list[EvidenceItem]:
    def score(item: EvidenceItem) -> int:
        lowered = (item.period_label or item.row_label).lower()
        if any(term in lowered for term in _PREVIOUS_TERMS):
            return 0
        if any(term in lowered for term in _CURRENT_TERMS):
            return 1
        return 2

    return sorted(items, key=score)


def _build_premise_claim(evidence: AnalysisEvidence) -> tuple[ApprovedClaim | None, str | None]:
    if not evidence.primary_metric or not evidence.metric_direction or not evidence.premise_hint:
        return None, None

    for source_alias, items in _group_items_by_source(evidence).items():
        matching = [
            item
            for item in items
            if evidence.primary_metric in item.metrics
            and item.step_category == "premise_check"
        ]
        if len(matching) < 2:
            matching = [
                item
                for item in items
                if evidence.primary_metric in item.metrics and not item.dimensions
            ]
        if len(matching) < 2:
            continue
        ordered = _sort_period_pair(matching[:2])
        left, right = ordered[0], ordered[1]
        left_value = _value_map(left).get(evidence.primary_metric) or _value_map(left).get(f"{left.row_label}.{evidence.primary_metric}")
        right_value = _value_map(right).get(evidence.primary_metric) or _value_map(right).get(f"{right.row_label}.{evidence.primary_metric}")
        if left_value is None or right_value is None:
            continue

        left_number = float(left_value)
        right_number = float(right_value)
        if evidence.metric_direction == "lower_is_better":
            performance_change = "improved" if right_number < left_number else "deteriorated" if right_number > left_number else "flat"
        elif evidence.metric_direction == "higher_is_better":
            performance_change = "improved" if right_number > left_number else "deteriorated" if right_number < left_number else "flat"
        else:
            performance_change = "flat"

        contradicted = (
            (evidence.premise_hint == "deterioration" and performance_change == "improved")
            or (evidence.premise_hint == "improvement" and performance_change == "deteriorated")
        )
        if contradicted:
            statement = (
                f"The premise is not supported. {evidence.primary_metric} was {left_value} for {left.row_label} and "
                f"{right_value} for {right.row_label}, and {evidence.metric_direction.replace('_', ' ')}."
            )
        else:
            statement = (
                f"The available evidence supports the primary comparison. {evidence.primary_metric} was {left_value} "
                f"for {left.row_label} and {right_value} for {right.row_label}, and {evidence.metric_direction.replace('_', ' ')}."
            )

        return (
            ApprovedClaim(
                id="claim_premise_check",
                kind="premise_check",
                statement=statement,
                entities=[entity for entity in [left.row_label, right.row_label, *left.entities, *right.entities] if entity],
                metrics=[evidence.primary_metric],
                source_aliases=[source_alias],
                values=[
                    EvidenceValue(label=f"{left.row_label}.{evidence.primary_metric}", value=left_value),
                    EvidenceValue(label=f"{right.row_label}.{evidence.primary_metric}", value=right_value),
                ],
            ),
            "contradicted_premise" if contradicted else None,
        )
    return None, None


def _build_comparison_claims(evidence: AnalysisEvidence) -> list[ApprovedClaim]:
    claims: list[ApprovedClaim] = []
    for source_alias, items in _group_items_by_source(evidence).items():
        if len(items) != 2 or any(item.dimensions for item in items):
            continue
        ordered = _sort_period_pair(items)
        left, right = ordered[0], ordered[1]
        common_metrics = [metric for metric in left.metrics if metric in right.metrics]
        for metric in common_metrics[:6]:
            left_value = _value_map(left).get(metric)
            right_value = _value_map(right).get(metric)
            if left_value is None or right_value is None:
                continue
            claim_id = f"claim_{source_alias}_{metric}"
            claims.append(
                ApprovedClaim(
                    id=claim_id,
                    kind="comparison",
                    statement=f"In {source_alias}, {metric} was {left_value} for {left.row_label} and {right_value} for {right.row_label}.",
                    entities=[entity for entity in [left.row_label, right.row_label, *left.entities, *right.entities] if entity],
                    metrics=[metric],
                    source_aliases=[source_alias],
                    values=[
                        EvidenceValue(label=f"{left.row_label}.{metric}", value=left_value),
                        EvidenceValue(label=f"{right.row_label}.{metric}", value=right_value),
                    ],
                )
            )
    return claims


def _build_grouped_period_comparison_claims(evidence: AnalysisEvidence) -> tuple[list[ApprovedClaim], set[str]]:
    claims: list[ApprovedClaim] = []
    covered_item_ids: set[str] = set()

    for source_alias, items in _group_items_by_source(evidence).items():
        comparable = [
            item
            for item in items
            if item.period_label and item.dimensions
        ]
        if len(comparable) < 2:
            continue

        grouped: dict[tuple[tuple[str, str], ...], list[EvidenceItem]] = defaultdict(list)
        for item in comparable:
            grouped[tuple(sorted(item.dimensions.items()))].append(item)

        for group_items in grouped.values():
            period_values = {item.period_label for item in group_items if item.period_label}
            if len(period_values) < 2:
                continue
            ordered = _sort_period_pair(group_items)[:2]
            left, right = ordered[0], ordered[1]
            common_metrics = [metric for metric in left.metrics if metric in right.metrics]
            if not common_metrics:
                continue
            group_label = " | ".join(left.dimensions.values()) or left.row_label
            for metric in common_metrics[:4]:
                left_value = _value_map(left).get(metric)
                right_value = _value_map(right).get(metric)
                if left_value is None or right_value is None:
                    continue
                claims.append(
                    ApprovedClaim(
                        id=f"claim_{source_alias}_{group_label}_{metric}".replace(" ", "_").replace("|", "_").lower(),
                        kind="comparison",
                        statement=(
                            f"For {group_label}, {metric} was {left_value} for {left.period_label} and "
                            f"{right_value} for {right.period_label}."
                        ),
                        entities=[entity for entity in [group_label, left.period_label, right.period_label, *left.entities, *right.entities] if entity],
                        metrics=[metric],
                        source_aliases=[source_alias],
                        values=[
                            EvidenceValue(label=f"{group_label}.{left.period_label}.{metric}", value=left_value),
                            EvidenceValue(label=f"{group_label}.{right.period_label}.{metric}", value=right_value),
                        ],
                    )
                )
                covered_item_ids.update({left.id, right.id})
    return claims[:8], covered_item_ids


def _build_row_observation_claims(evidence: AnalysisEvidence, covered_item_ids: set[str] | None = None) -> list[ApprovedClaim]:
    claims: list[ApprovedClaim] = []
    covered_item_ids = covered_item_ids or set()
    for item in evidence.items:
        if item.id in covered_item_ids:
            continue
        if not item.metrics:
            continue
        value_map = _value_map(item)
        metric_pairs = [f"{metric} = {value_map[metric]}" for metric in item.metrics if metric in value_map][:4]
        if not metric_pairs:
            continue
        metric_text = ", ".join(metric_pairs[:-1]) + (f", and {metric_pairs[-1]}" if len(metric_pairs) > 1 else metric_pairs[0])
        claims.append(
            ApprovedClaim(
                id=f"claim_{item.id}",
                kind="row_observation",
                statement=f"For {item.row_label}, {metric_text}.",
                entities=item.entities or [item.row_label],
                metrics=item.metrics,
                source_aliases=[item.source_alias],
                values=[
                    EvidenceValue(label=f"{item.row_label}.{metric}", value=value_map[metric])
                    for metric in item.metrics
                    if metric in value_map
                ],
            )
        )
    return claims[:8]


def _build_caveat_claims(unresolved_steps: list[dict[str, Any]]) -> list[ApprovedClaim]:
    def _step_expectation(step: dict[str, Any]) -> StepExpectation:
        return _as_expectation(step.get("expectation"))

    def _metric_text(expectation: StepExpectation) -> str:
        metrics = expectation.expected_metric_columns
        if not metrics:
            return "the required metric"
        return ", ".join(metrics)

    claims: list[ApprovedClaim] = []
    for step in unresolved_steps:
        status = step.get("status", "failed")
        purpose = str(step.get("purpose") or "a workflow step").strip()
        expectation = _step_expectation(step)
        validation_reason = str(step.get("validation_reason") or step.get("error") or "").lower()
        repaired = int(step.get("attempt") or 1) > 1

        if (
            expectation.step_category == "premise_check"
            and "missing expected columns" in validation_reason
            and expectation.expected_metric_columns
        ):
            subject = "the premise-check query" if not repaired else "the repaired premise-check query"
            statement = f"The workflow could not validate a reliable comparison because {subject} did not return the required metric {_metric_text(expectation)}."
        elif (
            expectation.step_category == "premise_check"
            and ("distinct periods" in validation_reason or "one comparable row per period" in validation_reason)
        ):
            subject = "the premise-check query" if not repaired else "the repaired premise-check query"
            statement = f"The workflow could not validate a reliable comparison because {subject} did not return a valid period-by-period result structure."
        elif status == "partial":
            statement = f"The workflow only validated a partially comparable result for {purpose}."
        elif status == "invalid":
            statement = f"The workflow could not validate a reliable result for {purpose}."
        else:
            statement = f"The workflow could not fully establish {purpose} from the available execution results."
        claims.append(
            ApprovedClaim(
                id=f"claim_caveat_{step.get('id', 'step')}",
                kind="caveat",
                statement=statement,
                source_aliases=[str(step.get("output_alias") or "")] if step.get("output_alias") else [],
            )
        )
    return claims


def _claims_conflict(claims: list[ApprovedClaim]) -> bool:
    values_by_label: dict[str, set[str]] = defaultdict(set)
    for claim in claims:
        for value in claim.values:
            values_by_label[value.label].add(value.value)
    return any(len(values) > 1 for values in values_by_label.values())


def build_approved_claims(
    evidence: AnalysisEvidence,
    unresolved_steps: list[dict[str, Any]] | None = None,
) -> tuple[list[ApprovedClaim], str]:
    """Build deterministic claims and the expected final answer status."""

    if not evidence.items:
        caveat_claims = _build_caveat_claims(unresolved_steps or [])
        return caveat_claims, "insufficient_evidence"

    claims: list[ApprovedClaim] = []
    expected_status = "answered"

    premise_claim, premise_status = _build_premise_claim(evidence)
    if premise_claim is not None:
        claims.append(premise_claim)

    claims.extend(_build_comparison_claims(evidence))
    grouped_claims, covered_item_ids = _build_grouped_period_comparison_claims(evidence)
    claims.extend(grouped_claims)
    claims.extend(_build_row_observation_claims(evidence, covered_item_ids=covered_item_ids))
    caveat_claims = _build_caveat_claims(unresolved_steps or [])
    claims.extend(caveat_claims)

    deduped: list[ApprovedClaim] = []
    seen_statements: set[str] = set()
    for claim in claims:
        if claim.statement in seen_statements:
            continue
        seen_statements.add(claim.statement)
        deduped.append(claim)

    substantive_claims = [claim for claim in deduped if claim.kind != "caveat"]
    if _claims_conflict(substantive_claims):
        expected_status = "conflicting_evidence"
    elif premise_status is not None:
        expected_status = premise_status
    elif substantive_claims and caveat_claims:
        expected_status = "partial_answer"
    elif substantive_claims:
        expected_status = "answered"
    else:
        expected_status = "insufficient_evidence"

    return deduped, expected_status


def _extract_numeric_tokens(text: str) -> set[str]:
    return set(re.findall(r"\b\d+(?:\.\d+)?\b", text))


def _candidate_entity_phrases(text: str) -> set[str]:
    candidates: set[str] = set()
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        for match in re.findall(r"\b[A-Za-z][A-Za-z]*(?:\s+[A-Za-z][A-Za-z]*)+\b", stripped):
            candidates.add(match.strip())
    return candidates


def _first_nonempty_line(text: str) -> str:
    return next((line.strip() for line in text.splitlines() if line.strip()), "")


def validate_rendered_analysis(
    response: AnalysisRenderResponse,
    approved_claims: list[ApprovedClaim],
    expected_status: str,
) -> None:
    """Reject rendered analysis that steps outside the approved claim set."""

    claim_by_id = {claim.id: claim for claim in approved_claims}
    used_ids = response.used_claim_ids or []
    if expected_status != "insufficient_evidence" and not used_ids:
        raise ValueError("The final analysis must cite at least one approved claim id.")
    unknown_ids = [claim_id for claim_id in used_ids if claim_id not in claim_by_id]
    if unknown_ids:
        raise ValueError(f"Unknown claim ids in used_claim_ids: {unknown_ids}")
    if response.answer_status != expected_status:
        raise ValueError(f"answer_status must be {expected_status}, got {response.answer_status}")

    selected_claims = [claim_by_id[claim_id] for claim_id in used_ids if claim_id in claim_by_id]
    if expected_status == "partial_answer" and not any(claim.kind == "caveat" for claim in selected_claims):
        raise ValueError("A partial answer must cite at least one caveat claim.")
    allowed_numbers = {
        token
        for claim in selected_claims
        for token in _extract_numeric_tokens(claim.statement)
    }
    unexpected_numbers = sorted(_extract_numeric_tokens(response.analysis_markdown) - allowed_numbers)
    if unexpected_numbers:
        raise ValueError(f"Analysis introduced numbers not present in the approved claims: {unexpected_numbers}")

    lowered_analysis = response.analysis_markdown.lower()
    for term in _BLOCKED_TERMS:
        if term in lowered_analysis:
            raise ValueError(f"Analysis used unsupported wording: {term}")
    for term in _INTERNAL_LEAK_TERMS:
        if term in lowered_analysis:
            raise ValueError(f"Analysis leaked internal workflow text: {term}")
    if re.search(r"\bclaim_[a-zA-Z0-9_]+\b", response.analysis_markdown):
        raise ValueError("Analysis leaked internal claim identifiers.")

    allowed_entities = {
        entity
        for claim in selected_claims
        for entity in claim.entities
        if entity
    }
    for candidate in _candidate_entity_phrases(response.analysis_markdown):
        if candidate in allowed_entities or candidate in _GENERIC_PROPER_NOUN_ALLOWLIST:
            continue
        similar = max(
            (
                SequenceMatcher(None, candidate.lower(), allowed.lower()).ratio()
                for allowed in allowed_entities
            ),
            default=0.0,
        )
        if similar >= 0.82:
            raise ValueError(f"Analysis changed an approved entity name: {candidate}")

    first_line = _first_nonempty_line(response.analysis_markdown)
    lowered_first_line = first_line.lower()
    if expected_status == "contradicted_premise":
        if "does not support" not in lowered_first_line and "contradict" not in lowered_first_line:
            raise ValueError("A contradicted premise must be stated clearly in the first sentence.")
    if expected_status == "answered" and any(claim.kind == "premise_check" for claim in selected_claims):
        if "supports" not in lowered_first_line and "answers" not in lowered_first_line and "shows" not in lowered_first_line:
            raise ValueError("A fully answered verdict should be stated clearly in the first sentence.")
