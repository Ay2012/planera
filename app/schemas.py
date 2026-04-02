"""Shared Pydantic schemas for API, planning, and execution contracts."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AnalyzeRequest(BaseModel):
    """Incoming analysis request."""

    query: str = Field(..., min_length=3, examples=["Why did pipeline velocity drop this week?"])


class TraceEvent(BaseModel):
    """Trace event for user-facing workflow visibility."""

    step: str
    status: Literal["started", "completed", "failed", "skipped"]
    details: dict[str, Any] = Field(default_factory=dict)


class ErrorItem(BaseModel):
    """Structured error payload kept in state and API responses."""

    step: str
    message: str
    recoverable: bool = True
    details: dict[str, Any] = Field(default_factory=dict)


class ArtifactSummary(BaseModel):
    """Compact artifact summary stored in state and returned to the UI."""

    alias: str
    artifact_type: Literal["table", "scalar", "text", "unknown"] = "unknown"
    row_count: int = 0
    columns: list[str] = Field(default_factory=list)
    preview_rows: list[dict[str, Any]] = Field(default_factory=list)
    summary: dict[str, Any] = Field(default_factory=dict)


class CompiledPlanStep(BaseModel):
    """One row in a compiled multi-step SQL plan."""

    model_config = ConfigDict(extra="forbid")

    id: int
    purpose: str = Field(..., min_length=1)
    type: Literal["sql"]
    query: str = Field(..., min_length=1)
    output_alias: str | None = None


class CompiledPlan(BaseModel):
    """Full planner output: up to three SQL steps in one response."""

    model_config = ConfigDict(extra="forbid")

    objective: str = Field(..., min_length=1)
    plan: list[CompiledPlanStep] = Field(..., min_length=1, max_length=3)
    max_steps: int
    metric: str
    metric_direction: str

    @field_validator("max_steps", mode="before")
    @classmethod
    def normalize_max_steps(cls, v: Any) -> int:
        """Models often set max_steps to the number of SQL steps; the contract is a fixed cap of 3."""
        return 3


class RepairDecision(BaseModel):
    """Planner repair output: replace one failed step."""

    model_config = ConfigDict(extra="forbid")

    repair_action: Literal["replace_step"]
    updated_step: CompiledPlanStep


class AnalysisNarrativeResponse(BaseModel):
    """Structured LLM output for the final user-facing narrative."""

    model_config = ConfigDict(extra="forbid")

    analysis: str = Field(..., min_length=1)


class ExecutedStep(BaseModel):
    """Execution log for one attempted step."""

    id: str
    kind: Literal["sql", "pandas"]
    purpose: str
    code: str
    output_alias: str
    attempt: int
    status: Literal["success", "failed"]
    artifact: ArtifactSummary | None = None
    error: str | None = None


class AnalyzeResponse(BaseModel):
    """Final API response for a completed analysis run."""

    analysis: str
    trace: list[TraceEvent]
    executed_steps: list[ExecutedStep]
    errors: list[ErrorItem]
    inspection_id: str | None = None


class HealthResponse(BaseModel):
    """Health endpoint response."""

    status: str
    app_name: str


class SampleQuestionsResponse(BaseModel):
    """Sample questions endpoint response."""

    questions: list[str]


class UploadedAsset(BaseModel):
    """Workspace upload summary returned to the React UI."""

    id: str
    name: str
    type: str
    source: str
    sizeLabel: str
    uploadedAt: str
    status: Literal["uploaded", "profiling", "verified", "error"]
    rows: int | None = None
    columns: int | None = None
    summary: str | None = None


class UploadResponse(BaseModel):
    """Upload endpoint response."""

    asset: UploadedAsset
    fallback: bool = False


class ResultTableData(BaseModel):
    """Tabular preview data for the inspection drawer."""

    columns: list[str]
    rows: list[dict[str, str | int | float | None]]


class TraceEntry(BaseModel):
    """One user-facing trace row for the inspection drawer."""

    id: str
    label: str
    description: str
    detail: str
    durationLabel: str
    status: Literal["valid", "warning", "error", "running", "complete"]


class ValidationCheck(BaseModel):
    """One validation summary item for the inspection drawer."""

    id: str
    label: str
    detail: str
    status: Literal["pass", "warn", "fail"]


class MetadataItem(BaseModel):
    """Compact metadata label/value pair for the inspection drawer."""

    label: str
    value: str


class InspectionData(BaseModel):
    """Detailed inspection payload used by the React UI."""

    id: str
    title: str
    query: str
    status: Literal["valid", "warning", "error", "running"]
    rowsReturned: int
    runtimeMs: int | None = None
    filters: list[str]
    confidence: float
    verified: bool
    dataSource: str
    lastUpdated: str
    engine: str
    queryType: str
    results: ResultTableData
    trace: list[TraceEntry]
    validation: list[ValidationCheck]
    metadata: list[MetadataItem]


class InspectionResponse(BaseModel):
    """Inspection endpoint response."""

    inspection: InspectionData
    fallback: bool = False
