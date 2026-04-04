import type {
  AnalyzeApiResponse,
  AnalyzeArtifactSummary,
  AnalyzeExecutedStep,
  AnalyzeTraceEvent,
} from "@/api/types";
import { shortId } from "@/lib/utils";
import type { AssistantPayload, ChatMessage, Insight, MetricCard } from "@/types/chat";
import type { InspectionData, InspectionStatus, ResultTableData, TraceEntry, ValidationCheck } from "@/types/inspection";

interface ParsedAnalysis {
  summary: string;
  details: string[];
}

const STEP_LABELS: Record<string, string> = {
  load_schema_context_node: "Schema Context",
  planner_compiled_node: "Query Planning",
  execute_plan_node: "Execution",
  analysis_node: "Narrative Synthesis",
  api_analyze: "API Analyze",
  repair_planner: "Repair Planning",
};

export function conversationTitleFromPrompt(prompt: string) {
  const compact = prompt.replace(/\s+/g, " ").trim();
  if (compact.length <= 56) return compact;
  return `${compact.slice(0, 53)}...`;
}

export function mapAnalyzeResponseToUi(prompt: string, response: AnalyzeApiResponse) {
  const inspectionId = response.inspection_id ?? shortId("inspect");
  const inspection = buildInspection(inspectionId, prompt, response);
  const payload = buildAssistantPayload(response, inspection);

  const message: ChatMessage = {
    id: shortId("msg"),
    role: "assistant",
    content: payload.summary,
    createdAt: inspection.lastUpdated,
    status: "ready",
    payload,
  };

  return {
    title: conversationTitleFromPrompt(prompt),
    inspection,
    message,
  };
}

function buildInspection(id: string, prompt: string, response: AnalyzeApiResponse): InspectionData {
  const executedSteps = response.executed_steps ?? [];
  const primaryArtifact = pickPrimaryArtifact(executedSteps);
  const results = artifactToTable(primaryArtifact);
  const rowsReturned = primaryArtifact?.row_count ?? 0;
  const confidence = deriveConfidence(response, primaryArtifact);
  const status = deriveInspectionStatus(response, executedSteps);
  const verified = status === "valid" && response.errors.length === 0 && executedSteps.some((step) => step.status === "success");
  const query = buildCodeBundle(executedSteps);
  const runtimeMs = null;

  return {
    id,
    title: conversationTitleFromPrompt(prompt),
    query,
    status,
    rowsReturned,
    runtimeMs,
    filters: buildExecutionChips(response, primaryArtifact),
    confidence,
    verified,
    dataSource: deriveDataSource(executedSteps),
    lastUpdated: new Date().toISOString(),
    engine: "DuckDB",
    queryType: deriveQueryType(executedSteps),
    results,
    trace: buildTraceEntries(response.trace),
    validation: buildValidation(response, primaryArtifact, confidence),
    metadata: buildMetadata(response, primaryArtifact, rowsReturned, results.columns.length, verified, runtimeMs),
  };
}

function buildAssistantPayload(response: AnalyzeApiResponse, inspection: InspectionData): AssistantPayload {
  const parsed = parseAnalysis(response.analysis);
  const primaryArtifact = pickPrimaryArtifact(response.executed_steps);
  const successCount = response.executed_steps.filter((step) => step.status === "success").length;
  const totalSteps = response.executed_steps.length;
  const repairedCount = response.executed_steps.filter((step) => step.attempt > 1).length;
  const insights = buildInsights(response, primaryArtifact, inspection);
  const metrics = buildMetrics(successCount, totalSteps, inspection.rowsReturned, inspection);

  const detailPool = [
    ...parsed.details,
    primaryArtifact
      ? `Preview ready for ${primaryArtifact.alias} with ${inspection.rowsReturned} row${inspection.rowsReturned === 1 ? "" : "s"} available in the inspection drawer.`
      : "The backend did not return a previewable artifact for this run.",
    repairedCount
      ? `${repairedCount} repair or retry attempt${repairedCount === 1 ? "" : "s"} was recorded while executing the workflow.`
      : response.errors.length
        ? `${response.errors.length} workflow issue${response.errors.length === 1 ? "" : "s"} was recorded in the backend response.`
        : "No workflow issues were reported in the backend response.",
    response.trace.length
      ? `${response.trace.length} workflow event${response.trace.length === 1 ? "" : "s"} is available in the trace tab.`
      : "No detailed trace events were returned for this run.",
  ];

  return {
    summary: parsed.summary,
    details: dedupe(detailPool).slice(0, 4),
    insights,
    metrics,
    previewTable: inspection.rowsReturned > 0 ? inspection.results : undefined,
    chart: buildChart(inspection.results),
    sqlPreview: inspection.query,
    recommendations: buildRecommendations(response, inspection, primaryArtifact),
    inspectionId: inspection.id,
    confidence: inspection.confidence,
    verificationLabel: inspection.verified ? "Verified" : inspection.status === "error" ? "Execution issue" : "Needs review",
    executionLabel:
      inspection.status === "valid"
        ? "DuckDB execution complete"
        : inspection.status === "warning"
          ? "Execution completed with review notes"
          : "Execution failed",
  };
}

function parseAnalysis(analysis: string): ParsedAnalysis {
  const rawLines = analysis
    .split(/\n+/)
    .map((line) => line.trim())
    .filter(Boolean);

  const paragraphLines: string[] = [];
  const bulletLines: string[] = [];

  for (const line of rawLines) {
    const cleaned = cleanMarkdown(line);
    if (!cleaned) continue;

    if (/^[-*+]\s+/.test(line) || /^\d+\.\s+/.test(line)) {
      bulletLines.push(cleaned);
      continue;
    }

    paragraphLines.push(cleaned);
  }

  const summary = paragraphLines[0] ?? bulletLines[0] ?? "Planera completed the requested analysis.";
  const details = dedupe([...paragraphLines.slice(1), ...bulletLines]).filter((line) => line !== summary);

  return {
    summary,
    details,
  };
}

function cleanMarkdown(value: string) {
  return value
    .replace(/^#{1,6}\s*/, "")
    .replace(/^[-*+]\s+/, "")
    .replace(/^\d+\.\s+/, "")
    .replace(/`([^`]+)`/g, "$1")
    .replace(/\*\*([^*]+)\*\*/g, "$1")
    .replace(/\*([^*]+)\*/g, "$1")
    .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
    .trim();
}

function buildInsights(
  response: AnalyzeApiResponse,
  primaryArtifact: AnalyzeArtifactSummary | null,
  inspection: InspectionData,
): Insight[] {
  const successCount = response.executed_steps.filter((step) => step.status === "success").length;
  const totalSteps = response.executed_steps.length;
  const repairedCount = response.executed_steps.filter((step) => step.attempt > 1).length;

  const insights: Insight[] = [];

  if (primaryArtifact) {
    insights.push({
      id: shortId("insight"),
      title: inspection.rowsReturned > 0 ? `${inspection.rowsReturned} rows are ready to inspect` : "Execution completed without rows",
      body:
        inspection.rowsReturned > 0
          ? `Planera surfaced ${inspection.rowsReturned} row${inspection.rowsReturned === 1 ? "" : "s"} from ${primaryArtifact.alias} across ${inspection.results.columns.length} column${inspection.results.columns.length === 1 ? "" : "s"}.`
          : `The workflow finished, but ${primaryArtifact.alias} did not return a non-empty result preview.`,
      tone: inspection.rowsReturned > 0 ? "positive" : "neutral",
    });
  }

  insights.push({
    id: shortId("insight"),
    title: repairedCount || response.errors.length ? "Execution needs a quick review" : "Execution stayed structurally clean",
    body:
      repairedCount || response.errors.length
        ? `The backend reported ${response.errors.length} issue${response.errors.length === 1 ? "" : "s"} and ${repairedCount} retry attempt${repairedCount === 1 ? "" : "s"}, so the trace should be reviewed before sharing broadly.`
        : `${successCount} of ${totalSteps || 0} executed step${totalSteps === 1 ? "" : "s"} completed successfully with no recorded workflow errors.`,
    tone: repairedCount || response.errors.length ? "caution" : "positive",
  });

  return insights.slice(0, 2);
}

function buildMetrics(successCount: number, totalSteps: number, rowsReturned: number, inspection: InspectionData): MetricCard[] {
  return [
    {
      id: "executed_steps",
      label: "Executed steps",
      value: totalSteps ? `${successCount}/${totalSteps}` : "0",
      change: totalSteps ? (totalSteps > successCount ? "Review trace" : "All completed") : "No executed steps",
    },
    {
      id: "rows_returned",
      label: "Rows returned",
      value: `${rowsReturned}`,
      change: rowsReturned > 0 ? "Preview available" : "No preview rows",
    },
    {
      id: "confidence",
      label: "Confidence",
      value: `${Math.round(inspection.confidence * 100)}%`,
      change: inspection.verified ? "Execution verified" : "Needs review",
    },
  ];
}

function buildRecommendations(
  response: AnalyzeApiResponse,
  inspection: InspectionData,
  primaryArtifact: AnalyzeArtifactSummary | null,
) {
  const recommendations = [
    inspection.status === "valid"
      ? "Open the inspection drawer to review the executed SQL and preview rows before sharing the conclusion."
      : "Review the trace and validation tabs before treating this answer as a final business conclusion.",
    inspection.rowsReturned > 5
      ? "Ask a narrower follow-up to focus the result set on one segment, owner, or time window."
      : "Use a follow-up prompt to slice the returned result by another business dimension.",
    response.errors.length || response.executed_steps.some((step) => step.attempt > 1)
      ? "Check the repaired or failed step details to understand where the workflow needed intervention."
      : primaryArtifact
        ? `Reuse the ${primaryArtifact.alias} result as a starting point for a deeper analyst review.`
        : "Retry with a more specific question if you need a richer result preview.",
  ];

  return recommendations;
}

function buildExecutionChips(response: AnalyzeApiResponse, primaryArtifact: AnalyzeArtifactSummary | null) {
  const executedSteps = response.executed_steps.length;
  const retryCount = response.executed_steps.filter((step) => step.attempt > 1).length;

  return dedupe(
    [
      executedSteps ? `${executedSteps} workflow step${executedSteps === 1 ? "" : "s"}` : "No executed steps",
      primaryArtifact ? `Output: ${primaryArtifact.alias}` : "No output alias",
      retryCount ? `${retryCount} retry attempt${retryCount === 1 ? "" : "s"}` : "No retries",
      response.errors.length ? `${response.errors.length} issue${response.errors.length === 1 ? "" : "s"}` : "No recorded errors",
    ].filter(Boolean),
  ).slice(0, 4);
}

function buildValidation(
  response: AnalyzeApiResponse,
  primaryArtifact: AnalyzeArtifactSummary | null,
  confidence: number,
): ValidationCheck[] {
  const successCount = response.executed_steps.filter((step) => step.status === "success").length;
  const totalSteps = response.executed_steps.length;
  const recoverableErrors = response.errors.filter((item) => item.recoverable).length;
  const fatalErrors = response.errors.filter((item) => !item.recoverable).length;
  const retryCount = response.executed_steps.filter((step) => step.attempt > 1).length;

  return [
    {
      id: "query_validity",
      label: "Query validity",
      detail: fatalErrors
        ? "The backend reported a non-recoverable workflow error during execution."
        : successCount > 0
          ? "At least one execution step completed successfully."
          : "No successful execution steps were returned for this prompt.",
      status: fatalErrors ? "fail" : successCount > 0 ? "pass" : "warn",
    },
    {
      id: "step_coverage",
      label: "Step coverage",
      detail: totalSteps
        ? `${successCount} of ${totalSteps} executed step${totalSteps === 1 ? "" : "s"} completed successfully.`
        : "The backend did not return any executed steps for this run.",
      status: totalSteps > 0 && successCount === totalSteps ? "pass" : successCount > 0 ? "warn" : "fail",
    },
    {
      id: "result_availability",
      label: "Result availability",
      detail: primaryArtifact?.row_count
        ? `The final artifact ${primaryArtifact.alias} returned ${primaryArtifact.row_count} row${primaryArtifact.row_count === 1 ? "" : "s"} and is available for inspection.`
        : "No non-empty preview artifact was returned by the backend response.",
      status: primaryArtifact?.row_count ? "pass" : "warn",
    },
    {
      id: "recovery_path",
      label: "Recovery path",
      detail:
        retryCount || recoverableErrors
          ? `The workflow used ${retryCount} retry attempt${retryCount === 1 ? "" : "s"} and reported ${recoverableErrors} recoverable issue${recoverableErrors === 1 ? "" : "s"}.`
          : "The workflow completed without repair or retry events.",
      status: retryCount || recoverableErrors ? "warn" : "pass",
    },
    {
      id: "execution_confidence",
      label: "Execution confidence",
      detail: "Confidence is derived from successful step coverage and artifact completeness for this run.",
      status: confidence >= 0.8 ? "pass" : confidence >= 0.6 ? "warn" : "fail",
    },
  ];
}

function buildMetadata(
  response: AnalyzeApiResponse,
  primaryArtifact: AnalyzeArtifactSummary | null,
  rowsReturned: number,
  columnCount: number,
  verified: boolean,
  runtimeMs: number | null,
) {
  const successCount = response.executed_steps.filter((step) => step.status === "success").length;
  const totalSteps = response.executed_steps.length;

  return [
    {
      label: "Execution status",
      value: response.errors.some((item) => !item.recoverable)
        ? "Failed"
        : response.errors.length || response.executed_steps.some((step) => step.attempt > 1)
          ? "Completed with review notes"
          : "Complete",
    },
    {
      label: "Verification",
      value: verified ? "Verified" : "Needs analyst review",
    },
    {
      label: "Output shape",
      value: rowsReturned > 0 ? `${rowsReturned} rows • ${columnCount} columns` : "No preview rows returned",
    },
    {
      label: "Step coverage",
      value: totalSteps ? `${successCount}/${totalSteps} successful` : "No executed steps",
    },
    {
      label: "Runtime",
      value: runtimeMs == null ? "Not reported by backend" : `${runtimeMs} ms`,
    },
    {
      label: "Primary artifact",
      value: primaryArtifact?.alias ?? "Unavailable",
    },
  ];
}

function buildTraceEntries(trace: AnalyzeTraceEvent[]): TraceEntry[] {
  return trace.map((event, index) => ({
    id: `${event.step}_${index}`,
    label: humanizeStepName(event.step),
    description: buildTraceDescription(event),
    detail: formatTraceDetails(event.details),
    durationLabel: statusLabel(event.status),
    status: mapTraceStatus(event.status),
  }));
}

function buildTraceDescription(event: AnalyzeTraceEvent) {
  if (typeof event.details.message === "string" && event.details.message) {
    return String(event.details.message);
  }

  if (event.status === "completed") {
    return `${humanizeStepName(event.step)} completed successfully.`;
  }

  if (event.status === "failed") {
    return `${humanizeStepName(event.step)} reported a workflow issue.`;
  }

  if (event.status === "skipped") {
    return `${humanizeStepName(event.step)} was skipped by the workflow.`;
  }

  return `${humanizeStepName(event.step)} started running.`;
}

function formatTraceDetails(details: Record<string, unknown>) {
  const pairs = Object.entries(details);
  if (!pairs.length) return "No additional structured details were returned for this step.";

  return pairs
    .map(([key, value]) => `${humanizeKey(key)}: ${formatUnknownValue(value)}`)
    .join(" • ");
}

function artifactToTable(artifact: AnalyzeArtifactSummary | null): ResultTableData {
  if (!artifact) {
    return {
      columns: ["status"],
      rows: [{ status: "No preview rows returned" }],
    };
  }

  if (!artifact.preview_rows.length) {
    return {
      columns: ["status"],
      rows: [{ status: "No preview rows returned" }],
    };
  }

  const firstRow = artifact.preview_rows[0] ?? null;
  const columns = artifact.columns.length ? artifact.columns : firstRow ? Object.keys(firstRow) : ["status"];
  const rows = artifact.preview_rows.map((row) => Object.fromEntries(columns.map((column) => [column, normalizeCell(row[column])])));

  return {
    columns,
    rows,
  };
}

function buildChart(results: ResultTableData) {
  if (results.columns.length < 2 || (results.columns.length === 1 && results.columns[0] === "status")) {
    return undefined;
  }

  const numericColumn = results.columns.find((column) => results.rows.some((row) => typeof row[column] === "number"));
  const labelColumn = results.columns.find((column) => column !== numericColumn);

  if (!numericColumn || !labelColumn) {
    return undefined;
  }

  const points = results.rows
    .map((row, index) => ({
      label: String(row[labelColumn] ?? `Row ${index + 1}`),
      value: typeof row[numericColumn] === "number" ? Number(row[numericColumn]) : Number.NaN,
    }))
    .filter((point) => Number.isFinite(point.value))
    .slice(0, 5);

  return points.length >= 2 ? points : undefined;
}

function pickPrimaryArtifact(steps: AnalyzeExecutedStep[]) {
  const successful = [...steps].reverse().filter((step) => step.status === "success" && step.artifact);
  return successful.find((step) => (step.artifact?.row_count ?? 0) > 0)?.artifact ?? successful[0]?.artifact ?? null;
}

function buildCodeBundle(steps: AnalyzeExecutedStep[]) {
  if (!steps.length) {
    return "-- No executed query text was returned by the backend.";
  }

  return steps
    .map((step, index) => {
      const header = `-- Step ${index + 1} • ${step.purpose} • ${step.status}${step.attempt > 1 ? ` • attempt ${step.attempt}` : ""}`;
      return `${header}\n${step.code.trim()}`;
    })
    .join("\n\n");
}

function deriveInspectionStatus(response: AnalyzeApiResponse, steps: AnalyzeExecutedStep[]): InspectionStatus {
  if (response.errors.some((item) => !item.recoverable) || (steps.length > 0 && !steps.some((step) => step.status === "success"))) {
    return "error";
  }

  if (
    response.errors.length > 0 ||
    response.trace.some((event) => event.status === "failed" || event.status === "skipped") ||
    steps.some((step) => step.status === "failed" || step.attempt > 1)
  ) {
    return "warning";
  }

  return "valid";
}

function deriveConfidence(response: AnalyzeApiResponse, primaryArtifact: AnalyzeArtifactSummary | null) {
  const totalSteps = response.executed_steps.length;
  const successCount = response.executed_steps.filter((step) => step.status === "success").length;
  const successRatio = totalSteps > 0 ? successCount / totalSteps : 0;
  const previewBonus = primaryArtifact?.row_count ? 0.16 : 0;
  const traceBonus = response.trace.some((event) => event.status === "completed") ? 0.07 : 0;
  const errorPenalty = response.errors.some((item) => !item.recoverable) ? 0.18 : response.errors.length ? 0.08 : 0;
  const score = 0.46 + successRatio * 0.24 + previewBonus + traceBonus - errorPenalty;

  return clamp(score, 0.35, 0.95);
}

function deriveDataSource(steps: AnalyzeExecutedStep[]) {
  for (const step of steps) {
    const match = step.code.match(/\bfrom\s+([a-zA-Z0-9_."-]+)/i);
    if (match?.[1]) {
      return match[1].replace(/"/g, "");
    }
  }

  return "Planera semantic model";
}

function deriveQueryType(steps: AnalyzeExecutedStep[]) {
  if (!steps.length) return "SQL";

  const kinds = new Set(steps.map((step) => step.kind));
  if (kinds.size === 1) {
    return [...kinds][0].toUpperCase();
  }

  return "Mixed execution";
}

function humanizeStepName(step: string) {
  if (STEP_LABELS[step]) return STEP_LABELS[step];

  return step
    .replace(/_node$/, "")
    .split("_")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function humanizeKey(key: string) {
  return key
    .split("_")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function statusLabel(status: AnalyzeTraceEvent["status"]) {
  if (status === "completed") return "Complete";
  if (status === "failed") return "Failed";
  if (status === "skipped") return "Skipped";
  return "Started";
}

function mapTraceStatus(status: AnalyzeTraceEvent["status"]): TraceEntry["status"] {
  if (status === "completed") return "complete";
  if (status === "failed") return "error";
  if (status === "skipped") return "warning";
  return "running";
}

function normalizeCell(value: unknown): string | number | null {
  if (value == null) return null;
  if (typeof value === "number" || typeof value === "string") return value;
  if (typeof value === "boolean") return value ? "true" : "false";
  return JSON.stringify(value);
}

function formatUnknownValue(value: unknown): string {
  if (Array.isArray(value)) return value.map((item) => formatUnknownValue(item)).join(", ");
  if (value == null) return "n/a";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function dedupe(values: string[]) {
  return [...new Set(values.map((value) => value.trim()).filter(Boolean))];
}

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value));
}
