"""Workspace-facing API helpers for uploads and inspection payloads."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from threading import Lock
from typing import Any
from uuid import uuid4

from app.data.registry import clear_source_registry, ingest_source
from app.data.semantic_model import clear_semantic_context_cache
from app.schemas import AnalyzeResponse, ArtifactSummary, InspectionData, MetadataItem, ResultTableData, TraceEntry, UploadedAsset, ValidationCheck


STEP_LABELS: dict[str, str] = {
    "load_schema_context_node": "Schema Context",
    "planner_compiled_node": "Query Planning",
    "planner_node": "Workflow Planning",
    "query_writer_node": "Query Writing",
    "execute_plan_node": "Execution",
    "executor_node": "Step Execution",
    "analysis_node": "Narrative Synthesis",
    "analyzer_node": "Final Analysis",
    "api_analyze": "API Analyze",
    "repair_planner": "Repair Planning",
    "replan_node": "Replanning",
    "best_effort_node": "Best Effort Answer",
}

_STORE_LOCK = Lock()
_INSPECTIONS: dict[str, InspectionData] = {}


def clear_workspace_state() -> None:
    """Reset in-memory upload/inspection storage for tests."""

    with _STORE_LOCK:
        _INSPECTIONS.clear()
    clear_source_registry()
    clear_semantic_context_cache()


def profile_upload(filename: str, content: bytes) -> UploadedAsset:
    """Persist an uploaded structured dataset to the source registry."""

    asset = ingest_source(filename, content)
    clear_semantic_context_cache()
    return asset


def store_inspection(prompt: str, response: AnalyzeResponse) -> tuple[str, InspectionData]:
    """Build and store an inspection payload in memory for same-session retrieval."""

    inspection = _build_inspection(_short_id("inspect"), prompt, response)
    with _STORE_LOCK:
        _INSPECTIONS[inspection.id] = inspection
    return inspection.id, inspection


def get_inspection(inspection_id: str) -> InspectionData | None:
    """Return a stored inspection payload by id."""

    with _STORE_LOCK:
        return _INSPECTIONS.get(inspection_id)


def _build_inspection(inspection_id: str, prompt: str, response: AnalyzeResponse) -> InspectionData:
    executed_steps = response.executed_steps or []
    primary_artifact = _pick_primary_artifact(response)
    results = _artifact_to_table(primary_artifact)
    rows_returned = primary_artifact.row_count if primary_artifact else 0
    confidence = _derive_confidence(response, primary_artifact)
    inspection_status = _derive_inspection_status(response)
    verified = (
        inspection_status == "valid"
        and len(response.errors) == 0
        and any(step.status == "success" for step in executed_steps)
    )
    runtime_ms = response.runtime_ms

    return InspectionData(
        id=inspection_id,
        title=_conversation_title_from_prompt(prompt),
        query=_build_code_bundle(response),
        status=inspection_status,
        rowsReturned=rows_returned,
        runtimeMs=runtime_ms,
        filters=_build_execution_chips(response, primary_artifact),
        confidence=confidence,
        verified=verified,
        dataSource=_derive_data_source(response),
        lastUpdated=_now_iso(),
        engine="DuckDB",
        queryType=_derive_query_type(response),
        results=results,
        trace=_build_trace_entries(response),
        validation=_build_validation(response, primary_artifact, confidence),
        metadata=_build_metadata(response, primary_artifact, rows_returned, len(results.columns), verified, runtime_ms),
    )


def _conversation_title_from_prompt(prompt: str) -> str:
    compact = " ".join(prompt.split()).strip()
    if len(compact) <= 56:
        return compact
    return f"{compact[:53]}..."


def _build_execution_chips(response: AnalyzeResponse, primary_artifact: ArtifactSummary | None) -> list[str]:
    executed_steps = len(response.executed_steps)
    retry_count = sum(1 for step in response.executed_steps if step.attempt > 1)
    return _dedupe(
        [
            f"{executed_steps} workflow step{'' if executed_steps == 1 else 's'}" if executed_steps else "No executed steps",
            f"Output: {primary_artifact.alias}" if primary_artifact else "No output alias",
            f"{retry_count} retry attempt{'' if retry_count == 1 else 's'}" if retry_count else "No retries",
            f"{len(response.errors)} issue{'' if len(response.errors) == 1 else 's'}" if response.errors else "No recorded errors",
        ]
    )[:4]


def _build_validation(
    response: AnalyzeResponse,
    primary_artifact: ArtifactSummary | None,
    confidence: float,
) -> list[ValidationCheck]:
    success_count = sum(1 for step in response.executed_steps if step.status == "success")
    total_steps = len(response.executed_steps)
    recoverable_errors = sum(1 for item in response.errors if item.recoverable)
    fatal_errors = sum(1 for item in response.errors if not item.recoverable)
    retry_count = sum(1 for step in response.executed_steps if step.attempt > 1)

    return [
        ValidationCheck(
            id="query_validity",
            label="Query validity",
            detail=(
                "The backend reported a non-recoverable workflow error during execution."
                if fatal_errors
                else "At least one execution step completed successfully."
                if success_count > 0
                else "No successful execution steps were returned for this prompt."
            ),
            status="fail" if fatal_errors else "pass" if success_count > 0 else "warn",
        ),
        ValidationCheck(
            id="step_coverage",
            label="Step coverage",
            detail=(
                f"{success_count} of {total_steps} executed step{'' if total_steps == 1 else 's'} completed successfully."
                if total_steps
                else "The backend did not return any executed steps for this run."
            ),
            status="pass" if total_steps > 0 and success_count == total_steps else "warn" if success_count > 0 else "fail",
        ),
        ValidationCheck(
            id="result_availability",
            label="Result availability",
            detail=(
                f"The final artifact {primary_artifact.alias} returned {primary_artifact.row_count} row{'' if primary_artifact.row_count == 1 else 's'} and is available for inspection."
                if primary_artifact and primary_artifact.row_count
                else "No non-empty preview artifact was returned by the backend response."
            ),
            status="pass" if primary_artifact and primary_artifact.row_count else "warn",
        ),
        ValidationCheck(
            id="recovery_path",
            label="Recovery path",
            detail=(
                f"The workflow used {retry_count} retry attempt{'' if retry_count == 1 else 's'} and reported {recoverable_errors} recoverable issue{'' if recoverable_errors == 1 else 's'}."
                if retry_count or recoverable_errors
                else "The workflow completed without repair or retry events."
            ),
            status="warn" if retry_count or recoverable_errors else "pass",
        ),
        ValidationCheck(
            id="execution_confidence",
            label="Execution confidence",
            detail="Confidence is derived from successful step coverage and artifact completeness for this run.",
            status="pass" if confidence >= 0.8 else "warn" if confidence >= 0.6 else "fail",
        ),
    ]


def _build_metadata(
    response: AnalyzeResponse,
    primary_artifact: ArtifactSummary | None,
    rows_returned: int,
    column_count: int,
    verified: bool,
    runtime_ms: int | None,
) -> list[MetadataItem]:
    success_count = sum(1 for step in response.executed_steps if step.status == "success")
    total_steps = len(response.executed_steps)

    return [
        MetadataItem(
            label="Execution status",
            value=(
                "Failed"
                if any(not item.recoverable for item in response.errors)
                else "Completed with review notes"
                if response.errors or any(step.attempt > 1 for step in response.executed_steps)
                else "Complete"
            ),
        ),
        MetadataItem(label="Verification", value="Verified" if verified else "Needs analyst review"),
        MetadataItem(
            label="Output shape",
            value=f"{rows_returned} rows x {column_count} columns" if rows_returned > 0 else "No preview rows returned",
        ),
        MetadataItem(
            label="Step coverage",
            value=f"{success_count}/{total_steps} successful" if total_steps else "No executed steps",
        ),
        MetadataItem(
            label="Runtime",
            value="Not reported by backend" if runtime_ms is None else f"{runtime_ms} ms",
        ),
        MetadataItem(label="Primary artifact", value=primary_artifact.alias if primary_artifact else "Unavailable"),
    ]


def _build_trace_entries(response: AnalyzeResponse) -> list[TraceEntry]:
    return [
        TraceEntry(
            id=f"{event.step}_{index}",
            label=_humanize_step_name(event.step),
            description=_build_trace_description(event.step, event.status, event.details),
            detail=_format_trace_details(event.details),
            durationLabel=_status_label(event.status),
            status=_map_trace_status(event.status),
        )
        for index, event in enumerate(response.trace)
    ]


def _build_trace_description(step: str, event_status: str, details: dict[str, Any]) -> str:
    message = details.get("message")
    if isinstance(message, str) and message:
        return message
    if event_status == "completed":
        return f"{_humanize_step_name(step)} completed successfully."
    if event_status == "failed":
        return f"{_humanize_step_name(step)} reported a workflow issue."
    if event_status == "skipped":
        return f"{_humanize_step_name(step)} was skipped by the workflow."
    return f"{_humanize_step_name(step)} started running."


def _format_trace_details(details: dict[str, Any]) -> str:
    if not details:
        return "No additional structured details were returned for this step."
    return " | ".join(f"{_humanize_key(key)}: {_format_unknown_value(value)}" for key, value in details.items())


def _artifact_to_table(artifact: ArtifactSummary | None) -> ResultTableData:
    if not artifact or not artifact.preview_rows:
        return ResultTableData(columns=["status"], rows=[{"status": "No preview rows returned"}])

    first_row = artifact.preview_rows[0] if artifact.preview_rows else None
    columns = artifact.columns or (list(first_row.keys()) if first_row else ["status"])
    rows = [
        {column: _normalize_cell(row.get(column)) for column in columns}
        for row in artifact.preview_rows
    ]
    return ResultTableData(columns=columns, rows=rows)


def _pick_primary_artifact(response: AnalyzeResponse) -> ArtifactSummary | None:
    successful = [step for step in reversed(response.executed_steps) if step.status == "success" and step.artifact is not None]
    for step in successful:
        if step.artifact and step.artifact.row_count > 0:
            return step.artifact
    return successful[0].artifact if successful else None


def _build_code_bundle(response: AnalyzeResponse) -> str:
    if not response.executed_steps:
        return "-- No executed query text was returned by the backend."

    blocks: list[str] = []
    for index, step in enumerate(response.executed_steps, start=1):
        attempt_suffix = f" | attempt {step.attempt}" if step.attempt > 1 else ""
        header = f"-- Step {index} | {step.purpose} | {step.status}{attempt_suffix}"
        blocks.append(f"{header}\n{step.code.strip()}")
    return "\n\n".join(blocks)


def _derive_inspection_status(response: AnalyzeResponse) -> str:
    steps = response.executed_steps
    if any(not item.recoverable for item in response.errors) or (steps and not any(step.status == "success" for step in steps)):
        return "error"
    if (
        response.errors
        or any(event.status in {"failed", "skipped"} for event in response.trace)
        or any(step.status == "failed" or step.attempt > 1 for step in steps)
    ):
        return "warning"
    return "valid"


def _derive_confidence(response: AnalyzeResponse, primary_artifact: ArtifactSummary | None) -> float:
    total_steps = len(response.executed_steps)
    success_count = sum(1 for step in response.executed_steps if step.status == "success")
    success_ratio = success_count / total_steps if total_steps > 0 else 0.0
    preview_bonus = 0.16 if primary_artifact and primary_artifact.row_count else 0.0
    trace_bonus = 0.07 if any(event.status == "completed" for event in response.trace) else 0.0
    error_penalty = 0.18 if any(not item.recoverable for item in response.errors) else 0.08 if response.errors else 0.0
    score = 0.46 + success_ratio * 0.24 + preview_bonus + trace_bonus - error_penalty
    return _clamp(score, 0.35, 0.95)


def _derive_data_source(response: AnalyzeResponse) -> str:
    for step in response.executed_steps:
        match = re.search(r"\bfrom\s+([a-zA-Z0-9_.\"-]+)", step.code, flags=re.IGNORECASE)
        if match and match.group(1):
            return match.group(1).replace('"', "")
    return "Planera semantic model"


def _derive_query_type(response: AnalyzeResponse) -> str:
    if not response.executed_steps:
        return "SQL"
    kinds = {step.kind for step in response.executed_steps}
    if len(kinds) == 1:
        return next(iter(kinds)).upper()
    return "Mixed execution"


def _humanize_step_name(step: str) -> str:
    if step in STEP_LABELS:
        return STEP_LABELS[step]
    return " ".join(part.capitalize() for part in step.removesuffix("_node").split("_") if part)


def _humanize_key(key: str) -> str:
    return " ".join(part.capitalize() for part in key.split("_") if part)


def _status_label(event_status: str) -> str:
    if event_status == "completed":
        return "Complete"
    if event_status == "failed":
        return "Failed"
    if event_status == "skipped":
        return "Skipped"
    return "Started"


def _map_trace_status(event_status: str) -> str:
    if event_status == "completed":
        return "complete"
    if event_status == "failed":
        return "error"
    if event_status == "skipped":
        return "warning"
    return "running"


def _normalize_cell(value: Any) -> str | int | float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float, str)):
        return value
    return json.dumps(value, default=str)


def _format_unknown_value(value: Any) -> str:
    if isinstance(value, list):
        return ", ".join(_format_unknown_value(item) for item in value)
    if value is None:
        return "n/a"
    if isinstance(value, dict):
        return json.dumps(value, default=str)
    return str(value)


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for raw in values:
        value = raw.strip()
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return min(maximum, max(minimum, value))


def _short_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:8]}"


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
