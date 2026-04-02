import type { ChatMessage, Conversation } from "@/types/chat";
import type { InspectionData } from "@/types/inspection";
import type { UploadedAsset } from "@/types/upload";

export interface ChatRequest {
  conversationId?: string;
  prompt: string;
  attachmentIds?: string[];
}

export interface ChatResponse {
  conversationId: string;
  title: string;
  message: ChatMessage;
  mode: "live" | "demo";
  fallback: boolean;
}

export interface ConversationsResponse {
  conversations: Conversation[];
  fallback: boolean;
}

export interface UploadResponse {
  asset: UploadedAsset;
  fallback: boolean;
}

export interface InspectionResponse {
  inspection: InspectionData;
  fallback: boolean;
}

export interface AnalyzeApiRequest {
  query: string;
}

export interface AnalyzeTraceEvent {
  step: string;
  status: "started" | "completed" | "failed" | "skipped";
  details: Record<string, unknown>;
}

export interface AnalyzeErrorItem {
  step: string;
  message: string;
  recoverable: boolean;
  details: Record<string, unknown>;
}

export interface AnalyzeArtifactSummary {
  alias: string;
  artifact_type: "table" | "scalar" | "text" | "unknown";
  row_count: number;
  columns: string[];
  preview_rows: Array<Record<string, unknown>>;
  summary: Record<string, unknown>;
}

export interface AnalyzeExecutedStep {
  id: string;
  kind: "sql" | "pandas";
  purpose: string;
  code: string;
  output_alias: string;
  attempt: number;
  status: "success" | "failed";
  artifact?: AnalyzeArtifactSummary | null;
  error?: string | null;
}

export interface AnalyzeApiResponse {
  analysis: string;
  trace: AnalyzeTraceEvent[];
  executed_steps: AnalyzeExecutedStep[];
  errors: AnalyzeErrorItem[];
}
