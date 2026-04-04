/**
 * Authenticated chat + conversation APIs.
 *
 * Real turns use **`POST /chat`** only. Types named `Analyze*` mirror the analysis payload shape
 * returned inside chat responses (and by the server's stateless `POST /analyze`); this module
 * does not call `/analyze` for product flows.
 */
import { requestWithAuth, ApiError } from "@/api/client";
import { cacheInspection } from "@/api/inspections";
import { conversationTitleFromPrompt, mapAnalyzeResponseToUi } from "@/api/mappers";
import type {
  AnalyzeApiResponse,
  ApiChatTurnResponse,
  ApiConversationDetailResponse,
  ApiConversationsListResponse,
  ApiMessage,
  ChatRequest,
  ChatResponse,
  ConversationsResponse,
} from "@/api/types";
import { seededConversations, buildAssistantMessage } from "@/data/mockChats";
import { isDemoOnlyMode, shouldFallbackToDemo } from "@/config/env";
import { shortId, sleep } from "@/lib/utils";
import type { ChatMessage, Conversation } from "@/types/chat";

/** Numeric backend conversation id (local drafts use shortId prefixes). */
export function isBackendConversationId(id: string): boolean {
  return id !== "" && /^\d+$/.test(id);
}

export async function fetchConversations(accessToken: string | null): Promise<ConversationsResponse> {
  await sleep(120);

  if (isDemoOnlyMode) {
    return {
      conversations: seededConversations,
      fallback: true,
    };
  }

  if (!accessToken) {
    return { conversations: [], fallback: false };
  }

  const raw = await requestWithAuth<ApiConversationsListResponse>("/conversations", accessToken);
  const conversations = raw.conversations.map(mapApiSummaryToConversation);
  return { conversations, fallback: false };
}

export async function fetchConversationDetail(accessToken: string, conversationId: string): Promise<Conversation> {
  if (isDemoOnlyMode) {
    const found = seededConversations.find((c) => c.id === conversationId);
    if (found) return found;
    throw new ApiError("Conversation not found in demo dataset.", 404);
  }

  const raw = await requestWithAuth<ApiConversationDetailResponse>(`/conversations/${conversationId}`, accessToken);
  return mapApiDetailToConversation(raw);
}

function mapApiSummaryToConversation(row: ApiConversationsListResponse["conversations"][number]): Conversation {
  return {
    id: String(row.id),
    title: row.title,
    updatedAt: row.updated_at,
    sourceLabel: "Connected backend",
    mode: "live",
    messages: [],
  };
}

function mapApiDetailToConversation(raw: ApiConversationDetailResponse): Conversation {
  const c = raw.conversation;
  return {
    id: String(c.id),
    title: c.title,
    updatedAt: c.updated_at,
    sourceLabel: "Connected backend",
    mode: "live",
    messages: mapApiMessagesToChatMessages(raw.messages),
  };
}

function mapApiMessagesToChatMessages(messages: ApiMessage[]): ChatMessage[] {
  const out: ChatMessage[] = [];
  for (let i = 0; i < messages.length; i++) {
    const m = messages[i];
    if (m.role === "user") {
      out.push({
        id: String(m.id),
        role: "user",
        content: m.content,
        createdAt: m.created_at,
        status: "ready",
      });
      continue;
    }
    let userPrompt = "";
    for (let j = i - 1; j >= 0; j--) {
      if (messages[j].role === "user") {
        userPrompt = messages[j].content;
        break;
      }
    }
    out.push(mapPersistedAssistantToChatMessage(m, userPrompt || "Analysis"));
  }
  return out;
}

function mapPersistedAssistantToChatMessage(m: ApiMessage, promptForInspection: string): ChatMessage {
  const response: AnalyzeApiResponse = {
    analysis: m.content,
    trace: (m.metadata_json?.trace as AnalyzeApiResponse["trace"]) ?? [],
    executed_steps: (m.metadata_json?.executed_steps as AnalyzeApiResponse["executed_steps"]) ?? [],
    errors: (m.metadata_json?.errors as AnalyzeApiResponse["errors"]) ?? [],
    inspection_id:
      typeof m.metadata_json?.inspection_id === "string" ? m.metadata_json.inspection_id : undefined,
  };
  const mapped = mapAnalyzeResponseToUi(promptForInspection, response);
  cacheInspection(mapped.inspection);
  return {
    ...mapped.message,
    id: String(m.id),
    createdAt: m.created_at,
  };
}

export async function submitChatPrompt(payload: ChatRequest, accessToken: string | null): Promise<ChatResponse> {
  if (isDemoOnlyMode) {
    await sleep(850);
    const message = buildAssistantMessage(payload.prompt);
    return {
      conversationId: payload.conversationId ?? shortId("chat"),
      title: conversationTitleFromPrompt(payload.prompt),
      message,
      mode: "demo",
      fallback: true,
    };
  }

  if (!accessToken) {
    throw new ApiError("Not authenticated.");
  }

  try {
    const body: Record<string, unknown> = { query: payload.prompt };
    if (payload.conversationId && isBackendConversationId(payload.conversationId)) {
      body.conversation_id = Number.parseInt(payload.conversationId, 10);
    }

    const raw = await requestWithAuth<ApiChatTurnResponse>("/chat", accessToken, {
      method: "POST",
      body: JSON.stringify(body),
    });

    const analyzeLike: AnalyzeApiResponse = {
      analysis: raw.analysis,
      trace: raw.trace,
      executed_steps: raw.executed_steps,
      errors: raw.errors,
      inspection_id: raw.inspection_id ?? undefined,
    };
    const mapped = mapAnalyzeResponseToUi(payload.prompt, analyzeLike);
    cacheInspection(mapped.inspection);

    const assistantMessage: ChatMessage = {
      ...mapped.message,
      id: String(raw.assistant_message.id),
      createdAt: raw.assistant_message.created_at,
    };

    return {
      conversationId: String(raw.conversation.id),
      title: raw.conversation.title,
      message: assistantMessage,
      mode: "live",
      fallback: false,
    };
  } catch (error) {
    if (!shouldFallbackToDemo) throw error;

    await sleep(850);
    const message = buildAssistantMessage(payload.prompt);
    return {
      conversationId: payload.conversationId ?? shortId("chat"),
      title: conversationTitleFromPrompt(payload.prompt),
      message,
      mode: "demo",
      fallback: true,
    };
  }
}

export function createConversationShell(title = "New analysis"): Conversation {
  return {
    id: shortId("chat"),
    title,
    updatedAt: new Date().toISOString(),
    sourceLabel: isDemoOnlyMode ? "Demo workspace" : "Workspace session",
    mode: isDemoOnlyMode ? "demo" : "live",
    messages: [],
  };
}
