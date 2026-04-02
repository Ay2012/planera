import type { AssistantPayload, ChatMessage, Conversation } from "@/types/chat";
import { inspectionLibrary } from "@/data/mockInsights";
import { resultTableLibrary, sqlLibrary } from "@/data/mockSql";
import { shortId } from "@/lib/utils";

type ScenarioKey = "pipeline" | "churn" | "anomalies";

function scenarioForPrompt(prompt: string): ScenarioKey {
  const value = prompt.toLowerCase();

  if (value.includes("churn")) return "churn";
  if (value.includes("anomal")) return "anomalies";
  return "pipeline";
}

function buildPayload(prompt: string): AssistantPayload {
  const scenario = scenarioForPrompt(prompt);

  if (scenario === "churn") {
    return {
      summary: "SMB churn is the clearest source of drag this quarter, with materially higher churn than mid-market and enterprise.",
      details: [
        "SMB shows the highest churn rate in the inspected output and the weakest expansion profile.",
        "Enterprise remains comparatively stable, which suggests the issue is concentrated in lower-value cohorts.",
      ],
      insights: [
        {
          id: "insight_churn_1",
          title: "SMB is the pressure point",
          body: "SMB churn sits well above the rest of the business, making it the first segment to investigate for recent onboarding or pricing friction.",
          tone: "caution",
        },
        {
          id: "insight_churn_2",
          title: "Expansion remains strongest in enterprise",
          body: "Expansion MRR is healthiest at the top end of the market, reinforcing that retention issues are not evenly distributed.",
          tone: "neutral",
        },
      ],
      metrics: [
        { id: "m1", label: "Highest churn", value: "6.1%", change: "SMB" },
        { id: "m2", label: "Enterprise churn", value: "1.8%", change: "Stable" },
        { id: "m3", label: "Confidence", value: "87%", change: "Verified" },
      ],
      previewTable: resultTableLibrary.churn,
      chart: [
        { label: "SMB", value: 6.1 },
        { label: "Mid-market", value: 3.9 },
        { label: "Enterprise", value: 1.8 },
      ],
      sqlPreview: sqlLibrary.churn,
      recommendations: [
        "Review SMB onboarding and recent pricing changes.",
        "Segment churn by acquisition channel next.",
        "Inspect renewal cohorts with declining expansion MRR.",
      ],
      inspectionId: "inspect_churn_segment",
      confidence: 0.87,
      verificationLabel: "Verified",
      executionLabel: "Query complete",
    };
  }

  if (scenario === "anomalies") {
    return {
      summary: "Checkout conversion and day-7 activation are the top anomalies this week, but the result should be reviewed before broad rollout.",
      details: [
        "The system ranked recent anomalies by severity and surfaced three issues with the strongest deviation from baseline.",
        "Confidence is slightly lower because recent baseline context is thinner than ideal.",
      ],
      insights: [
        {
          id: "insight_anomaly_1",
          title: "Checkout conversion is the loudest signal",
          body: "Its anomaly score is materially higher than the rest of the observed issues, suggesting recent funnel regression.",
          tone: "caution",
        },
        {
          id: "insight_anomaly_2",
          title: "Treat this as a review queue",
          body: "This is useful for triage, but it should not be treated as a fully verified executive summary yet.",
          tone: "neutral",
        },
      ],
      metrics: [
        { id: "m1", label: "Top anomaly score", value: "0.94", change: "Checkout conversion" },
        { id: "m2", label: "Verification", value: "Partial", change: "Needs review" },
        { id: "m3", label: "Runtime", value: "744 ms", change: "Postgres" },
      ],
      previewTable: resultTableLibrary.anomalies,
      chart: [
        { label: "Checkout", value: 0.94 },
        { label: "Activation", value: 0.88 },
        { label: "Refunds", value: 0.77 },
      ],
      sqlPreview: sqlLibrary.anomalies,
      recommendations: [
        "Pull a longer baseline for the top anomalies.",
        "Check release timing against checkout conversion movement.",
        "Escalate checkout and activation to product ops for manual review.",
      ],
      inspectionId: "inspect_anomalies",
      confidence: 0.76,
      verificationLabel: "Needs review",
      executionLabel: "Trace complete",
    };
  }

  return {
    summary: "Enterprise conversion is dropping faster than the rest of the pipeline, with a 5.2 point decline versus the prior two-week window.",
    details: [
      "The inspected result set points to enterprise as the segment with the sharpest conversion softening.",
      "Mid-market also slipped, but not enough to explain the full movement on its own.",
    ],
    insights: [
      {
        id: "insight_pipe_1",
        title: "Enterprise is leading the decline",
        body: "Enterprise conversion fell from 22.4% to 17.2%, which is the largest segment-level change in the inspected result set.",
        tone: "caution",
      },
      {
        id: "insight_pipe_2",
        title: "This is concentrated, not broad collapse",
        body: "SMB remained comparatively steady, which suggests the issue is isolated enough for targeted investigation.",
        tone: "positive",
      },
    ],
    metrics: [
      { id: "m1", label: "Enterprise delta", value: "-5.2 pts", change: "Largest drop" },
      { id: "m2", label: "Rows returned", value: "3", change: "Segment comparison" },
      { id: "m3", label: "Confidence", value: "92%", change: "Verified" },
    ],
    previewTable: resultTableLibrary.pipeline,
    chart: [
      { label: "Enterprise", value: 17.2 },
      { label: "Mid-market", value: 23.1 },
      { label: "SMB", value: 28.9 },
    ],
    sqlPreview: sqlLibrary.pipeline,
    recommendations: [
      "Inspect late-stage enterprise handoff next.",
      "Review rep coverage and pricing exceptions for enterprise opportunities.",
      "Compare enterprise conversion by owner to isolate operational hotspots.",
    ],
    inspectionId: "inspect_pipeline_drop",
    confidence: 0.92,
    verificationLabel: "Verified",
    executionLabel: "Snowflake query complete",
  };
}

export function buildAssistantMessage(prompt: string): ChatMessage {
  const payload = buildPayload(prompt);

  return {
    id: shortId("msg"),
    role: "assistant",
    content: payload.summary,
    createdAt: new Date().toISOString(),
    status: "ready",
    payload,
  };
}

export const seededConversations: Conversation[] = [
  {
    id: "chat_conversion_drop",
    title: "Why is pipeline conversion dropping?",
    updatedAt: "2026-03-25T10:22:00.000Z",
    sourceLabel: "Connected warehouse",
    mode: "demo",
    messages: [
      {
        id: "msg_user_seed_1",
        role: "user",
        content: "Why is pipeline conversion dropping?",
        createdAt: "2026-03-25T10:21:00.000Z",
        status: "ready",
      },
      {
        id: "msg_assistant_seed_1",
        role: "assistant",
        content: "Enterprise conversion is dropping faster than the rest of the pipeline, with a 5.2 point decline versus the prior two-week window.",
        createdAt: "2026-03-25T10:22:00.000Z",
        status: "ready",
        payload: buildPayload("Why is pipeline conversion dropping?"),
      },
    ],
  },
  {
    id: "chat_churn_segment",
    title: "Show churn by segment",
    updatedAt: "2026-03-24T15:28:00.000Z",
    sourceLabel: "Uploaded CSV",
    mode: "demo",
    messages: [
      {
        id: "msg_user_seed_2",
        role: "user",
        content: "Show churn by segment",
        createdAt: "2026-03-24T15:25:00.000Z",
        status: "ready",
      },
      {
        id: "msg_assistant_seed_2",
        role: "assistant",
        content: "SMB churn is the clearest source of drag this quarter, with materially higher churn than mid-market and enterprise.",
        createdAt: "2026-03-24T15:28:00.000Z",
        status: "ready",
        payload: buildPayload("Show churn by segment"),
      },
    ],
  },
  {
    id: "chat_anomalies",
    title: "Summarize top anomalies",
    updatedAt: "2026-03-23T11:12:00.000Z",
    sourceLabel: "Demo dataset",
    mode: "demo",
    messages: [
      {
        id: "msg_user_seed_3",
        role: "user",
        content: "Summarize top anomalies",
        createdAt: "2026-03-23T11:08:00.000Z",
        status: "ready",
      },
      {
        id: "msg_assistant_seed_3",
        role: "assistant",
        content: "Checkout conversion and day-7 activation are the top anomalies this week, but the result should be reviewed before broad rollout.",
        createdAt: "2026-03-23T11:12:00.000Z",
        status: "ready",
        payload: buildPayload("Summarize top anomalies"),
      },
    ],
  },
];

export function getInspectionFromPrompt(prompt: string) {
  const scenario = scenarioForPrompt(prompt);

  if (scenario === "churn") return inspectionLibrary.inspect_churn_segment;
  if (scenario === "anomalies") return inspectionLibrary.inspect_anomalies;
  return inspectionLibrary.inspect_pipeline_drop;
}
