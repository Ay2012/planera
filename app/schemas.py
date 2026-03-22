"""Shared Pydantic schemas for API, planning, and execution contracts."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


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

    id: int
    purpose: str
    type: Literal["sql"] = "sql"
    query: str
    output_alias: str | None = None


class CompiledPlan(BaseModel):
    """Full planner output: up to three SQL steps in one response."""

    objective: str
    plan: list[CompiledPlanStep] = Field(default_factory=list)
    max_steps: int = 3
    metric: str = ""
    metric_direction: str = ""

    @field_validator("plan")
    @classmethod
    def cap_plan_length(cls, v: list[CompiledPlanStep]) -> list[CompiledPlanStep]:
        if len(v) > 3:
            raise ValueError("plan must contain at most 3 steps")
        return v

    @field_validator("max_steps", mode="before")
    @classmethod
    def normalize_max_steps(cls, v: Any) -> int:
        """Models often set max_steps to the number of SQL steps; the contract is a fixed cap of 3."""
        return 3


class RepairDecision(BaseModel):
    """Planner repair output: replace one failed step."""

    repair_action: Literal["replace_step"]
    updated_step: CompiledPlanStep


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


class HealthResponse(BaseModel):
    """Health endpoint response."""

    status: str
    app_name: str


class SampleQuestionsResponse(BaseModel):
    """Sample questions endpoint response."""

    questions: list[str]
