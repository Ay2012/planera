import { request } from "@/api/client";
import { cacheInspection } from "@/api/inspections";
import { conversationTitleFromPrompt, mapAnalyzeResponseToUi } from "@/api/mappers";
import type { AnalyzeApiRequest, AnalyzeApiResponse, ChatRequest, ChatResponse, ConversationsResponse } from "@/api/types";
import { seededConversations, buildAssistantMessage } from "@/data/mockChats";
import { shouldFallbackToDemo } from "@/config/env";
import { shortId, sleep } from "@/lib/utils";
import type { Conversation } from "@/types/chat";

export async function fetchConversations(): Promise<ConversationsResponse> {
  await sleep(120);
  return {
    conversations: shouldFallbackToDemo ? seededConversations : [],
    fallback: shouldFallbackToDemo,
  };
}

export async function submitChatPrompt(payload: ChatRequest): Promise<ChatResponse> {
  try {
    const requestBody: AnalyzeApiRequest = { query: payload.prompt };
    const response = await request<AnalyzeApiResponse>("/analyze", {
      method: "POST",
      body: JSON.stringify(requestBody),
    });
    const mapped = mapAnalyzeResponseToUi(payload.prompt, response);
    cacheInspection(mapped.inspection);

    return {
      conversationId: payload.conversationId ?? shortId("chat"),
      title: mapped.title,
      message: mapped.message,
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
    sourceLabel: "Untitled workspace",
    mode: "demo",
    messages: [],
  };
}
