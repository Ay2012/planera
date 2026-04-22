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

/** Body for the server's stateless `POST /analyze` (debug only — the UI sends `POST /chat` instead). */
export interface AnalyzeApiRequest {
  query: string;
  source_ids?: string[];
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

/**
 * Analysis payload shape shared by `POST /chat` (and the debug `POST /analyze` response).
 * Naming reflects backend fields, not a requirement to call `/analyze`.
 */
export interface AnalyzeApiResponse {
  analysis: string;
  trace: AnalyzeTraceEvent[];
  executed_steps: AnalyzeExecutedStep[];
  errors: AnalyzeErrorItem[];
  inspection_id?: string;
  /** Wall-clock run time of the graph (ms), from the backend. */
  runtime_ms?: number | null;
}

/** GET /conversations row (backend snake_case). */
export interface ApiConversationSummary {
  id: number;
  title: string;
  updated_at: string;
  last_message_preview: string | null;
}

export interface ApiConversationsListResponse {
  conversations: ApiConversationSummary[];
}

/** GET /conversations/{id} message (backend snake_case). */
export interface ApiMessage {
  id: number;
  role: "user" | "assistant";
  content: string;
  created_at: string;
  metadata_json: Record<string, unknown> | null;
}

export interface ApiConversationPublic {
  id: number;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface ApiConversationDetailResponse {
  conversation: ApiConversationPublic;
  messages: ApiMessage[];
}

/** POST /chat response (backend snake_case). */
export interface ApiChatTurnResponse {
  conversation: ApiConversationPublic;
  assistant_message: {
    id: number;
    role: "assistant";
    content: string;
    created_at: string;
    status: string;
    metadata_json: Record<string, unknown> | null;
  };
  analysis: string;
  trace: AnalyzeTraceEvent[];
  executed_steps: AnalyzeExecutedStep[];
  errors: AnalyzeErrorItem[];
  inspection_id: string | null;
  /** Omitted on very old clients; use null when absent. */
  runtime_ms?: number | null;
}
