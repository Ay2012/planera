"""Deterministic evidence, claims, and validation for grounded analysis output."""

from __future__ import annotations

import re
from collections import defaultdict
from difflib import SequenceMatcher
from numbers import Real
from typing import Any

from app.agent.state import AnalysisState
from app.schemas import AnalysisEvidence, AnalysisRenderResponse, ApprovedClaim, EvidenceItem, EvidenceValue

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


def _row_label(row: dict[str, Any], non_numeric_columns: list[str], fallback: str) -> str:
    values = [str(row[column]) for column in non_numeric_columns if row.get(column) not in (None, "")]
    if not values:
        return fallback
    if len(values) == 1:
        return values[0]
    return " | ".join(values)


def _extract_entities(row: dict[str, Any], non_numeric_columns: list[str]) -> list[str]:
    seen: list[str] = []
    for column in non_numeric_columns:
        value = row.get(column)
        if value in (None, ""):
            continue
        as_text = str(value)
        if as_text not in seen:
            seen.append(as_text)
    return seen


def build_analysis_evidence(state: AnalysisState) -> AnalysisEvidence:
    """Build a compact, domain-agnostic evidence packet from executed step previews."""

    items: list[EvidenceItem] = []
    allowed_entities: list[str] = []

    for step in state.get("executed_steps") or []:
        if step.get("status") != "success":
            continue
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

        for index, row in enumerate(preview_rows, start=1):
            entities = _extract_entities(row, non_numeric_columns)
            for entity in entities:
                if entity not in allowed_entities:
                    allowed_entities.append(entity)
            values = [EvidenceValue(label=column, value=_format_value(row.get(column))) for column in columns if row.get(column) is not None]
            items.append(
                EvidenceItem(
                    id=f"{artifact.get('alias', step['output_alias'])}_row_{index}",
                    source_alias=artifact.get("alias", step["output_alias"]),
                    source_purpose=step["purpose"],
                    row_label=_row_label(row, non_numeric_columns, fallback=f"row_{index}"),
                    entities=entities,
                    metrics=numeric_columns,
                    values=values,
                )
            )

    return AnalysisEvidence(
        question=state["query"],
        primary_metric=state.get("metric", ""),
        metric_direction=(state.get("compiled_plan") or {}).get("metric_direction", ""),
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
        lowered = item.row_label.lower()
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
        matching = [item for item in items if evidence.primary_metric in item.metrics]
        if len(matching) < 2:
            continue
        ordered = _sort_period_pair(matching[:2])
        left, right = ordered[0], ordered[1]
        left_value = _value_map(left).get(evidence.primary_metric)
        right_value = _value_map(right).get(evidence.primary_metric)
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
        statement = (
            f"The primary metric {evidence.primary_metric} was {left_value} for {left.row_label} and {right_value} for {right.row_label}. "
            f"The metric direction is {evidence.metric_direction}."
        )
        if contradicted:
            statement += f" This does not support a {evidence.premise_hint} premise."

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
        if len(items) != 2:
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


def _build_row_observation_claims(evidence: AnalysisEvidence) -> list[ApprovedClaim]:
    claims: list[ApprovedClaim] = []
    for item in evidence.items:
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
                values=[EvidenceValue(label=metric, value=value_map[metric]) for metric in item.metrics if metric in value_map],
            )
        )
    return claims[:8]


def build_approved_claims(evidence: AnalysisEvidence) -> tuple[list[ApprovedClaim], str]:
    """Build deterministic claims and the expected final answer status."""

    if not evidence.items:
        return [], "insufficient_evidence"

    claims: list[ApprovedClaim] = []
    expected_status = "answered"

    premise_claim, premise_status = _build_premise_claim(evidence)
    if premise_claim is not None:
        claims.append(premise_claim)
    if premise_status is not None:
        expected_status = premise_status

    claims.extend(_build_comparison_claims(evidence))
    claims.extend(_build_row_observation_claims(evidence))

    deduped: list[ApprovedClaim] = []
    seen_statements: set[str] = set()
    for claim in claims:
        if claim.statement in seen_statements:
            continue
        seen_statements.add(claim.statement)
        deduped.append(claim)

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

    if expected_status == "contradicted_premise":
        first_line = next((line.strip() for line in response.analysis_markdown.splitlines() if line.strip()), "")
        lowered_first_line = first_line.lower()
        if "does not support" not in lowered_first_line and "contradict" not in lowered_first_line:
            raise ValueError("A contradicted premise must be stated clearly in the first sentence.")
