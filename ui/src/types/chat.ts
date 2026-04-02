import type { ResultTableData } from "@/types/inspection";
import type { UploadedAsset } from "@/types/upload";

export type MessageRole = "user" | "assistant";

export interface Insight {
  id: string;
  title: string;
  body: string;
  tone?: "neutral" | "positive" | "caution";
}

export interface MetricCard {
  id: string;
  label: string;
  value: string;
  change: string;
}

export interface ChartPoint {
  label: string;
  value: number;
}

export interface AssistantPayload {
  summary: string;
  details: string[];
  insights: Insight[];
  metrics: MetricCard[];
  previewTable?: ResultTableData;
  chart?: ChartPoint[];
  sqlPreview?: string;
  recommendations: string[];
  inspectionId?: string;
  confidence?: number;
  verificationLabel?: string;
  executionLabel?: string;
}

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  createdAt: string;
  status?: "ready" | "sending" | "error";
  payload?: AssistantPayload;
  attachments?: UploadedAsset[];
}

export interface Conversation {
  id: string;
  title: string;
  updatedAt: string;
  sourceLabel: string;
  mode: "live" | "demo";
  messages: ChatMessage[];
}

export interface SavedAnalysis {
  id: string;
  title: string;
  summary: string;
  updatedAt: string;
  status: "verified" | "review" | "draft";
}
