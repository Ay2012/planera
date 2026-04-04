"""Shared Pydantic schemas for API, planning, and execution contracts."""

from __future__ import annotations

from datetime import datetime
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


class SchemaConceptMapping(BaseModel):
    """Heuristic business-language alias mapped to exact schema fields."""

    model_config = ConfigDict(extra="forbid")

    concept: str = Field(..., min_length=1)
    columns: list[str] = Field(default_factory=list)
    confidence: Literal["heuristic", "explicit"] = "heuristic"


class SchemaColumn(BaseModel):
    """Normalized schema field description used by the planner."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1)
    dtype: str = Field(..., min_length=1)
    type_family: Literal["string", "number", "boolean", "datetime", "unknown"] = "unknown"
    semantic_hints: list[str] = Field(default_factory=list)


class SchemaRelation(BaseModel):
    """One normalized table or view available to the planner."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1)
    kind: Literal["table", "view"] = "view"
    row_count: int = 0
    grain: str = ""
    identifier_columns: list[str] = Field(default_factory=list)
    time_columns: list[str] = Field(default_factory=list)
    measure_columns: list[str] = Field(default_factory=list)
    dimension_columns: list[str] = Field(default_factory=list)
    columns: list[SchemaColumn] = Field(default_factory=list)
    semantic_mappings: list[SchemaConceptMapping] = Field(default_factory=list)


class SchemaManifest(BaseModel):
    """Source-agnostic schema manifest consumed by the planner."""

    model_config = ConfigDict(extra="forbid")

    reference_date: str = ""
    source: str = ""
    dialect: str = ""
    relations: list[SchemaRelation] = Field(default_factory=list)
    views: list[dict[str, Any]] = Field(default_factory=list)


class EvidenceValue(BaseModel):
    """One exact label/value pair carried into the analysis evidence packet."""

    model_config = ConfigDict(extra="forbid")

    label: str = Field(..., min_length=1)
    value: str = Field(..., min_length=1)


class EvidenceItem(BaseModel):
    """One deterministic evidence row extracted from a successful artifact preview."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., min_length=1)
    source_alias: str = Field(..., min_length=1)
    source_purpose: str = Field(..., min_length=1)
    row_label: str = Field(..., min_length=1)
    entities: list[str] = Field(default_factory=list)
    metrics: list[str] = Field(default_factory=list)
    values: list[EvidenceValue] = Field(default_factory=list)


class AnalysisEvidence(BaseModel):
    """Compact, domain-agnostic evidence passed into the analysis layer."""

    model_config = ConfigDict(extra="forbid")

    question: str = Field(..., min_length=1)
    primary_metric: str = ""
    metric_direction: str = ""
    premise_hint: str = ""
    items: list[EvidenceItem] = Field(default_factory=list)
    allowed_entities: list[str] = Field(default_factory=list)


class ApprovedClaim(BaseModel):
    """Deterministic claim approved for final narrative rendering."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., min_length=1)
    kind: Literal["premise_check", "comparison", "row_observation", "caveat"]
    statement: str = Field(..., min_length=1)
    entities: list[str] = Field(default_factory=list)
    metrics: list[str] = Field(default_factory=list)
    source_aliases: list[str] = Field(default_factory=list)
    values: list[EvidenceValue] = Field(default_factory=list)


class AnalysisRenderResponse(BaseModel):
    """Structured LLM output for the final user-facing narrative."""

    model_config = ConfigDict(extra="forbid")

    answer_status: Literal["answered", "insufficient_evidence", "contradicted_premise", "conflicting_evidence"]
    analysis_markdown: str = Field(..., min_length=1)
    used_claim_ids: list[str] = Field(default_factory=list)


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


MessageRoleLiteral = Literal["user", "assistant"]


class ConversationSummary(BaseModel):
    """Sidebar-ready conversation row."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    updated_at: datetime
    last_message_preview: str | None = None


class ConversationsListResponse(BaseModel):
    conversations: list[ConversationSummary]


class MessagePublic(BaseModel):
    """One persisted chat message."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    role: MessageRoleLiteral
    content: str
    created_at: datetime
    metadata_json: dict[str, Any] | None = None


class ConversationPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    created_at: datetime
    updated_at: datetime


class ConversationDetailResponse(BaseModel):
    """Single conversation with ordered messages."""

    conversation: ConversationPublic
    messages: list[MessagePublic]


class ChatSubmitRequest(BaseModel):
    """Authenticated chat turn: optional thread id plus user query."""

    conversation_id: int | str | None = None
    query: str = Field(..., min_length=3)

    @field_validator("conversation_id", mode="before")
    @classmethod
    def normalize_conversation_id(cls, v: Any) -> int | None:
        if v is None:
            return None
        if isinstance(v, bool):
            raise ValueError("conversation_id must be an integer")
        if isinstance(v, int):
            return v
        if isinstance(v, str):
            s = v.strip()
            if not s:
                return None
            return int(s)
        raise ValueError("conversation_id must be an integer or numeric string")


class ChatAssistantMessagePublic(BaseModel):
    """Assistant row returned after a chat turn (persists alongside analysis fields)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    role: MessageRoleLiteral = "assistant"
    content: str
    created_at: datetime
    status: Literal["ready", "sending", "error"] = "ready"
    metadata_json: dict[str, Any] | None = None


class ChatTurnResponse(BaseModel):
    """POST /chat response: persisted thread + analysis payload."""

    conversation: ConversationPublic
    assistant_message: ChatAssistantMessagePublic
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
