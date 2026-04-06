import { useCallback, useEffect, useMemo, useState } from "react";
import {
  createConversationShell,
  fetchConversationDetail,
  fetchConversations,
  isBackendConversationId,
  submitChatPrompt,
} from "@/api/chat";
import { useAuth } from "@/hooks/useAuth";
import { uiStore } from "@/store/uiStore";
import type { ChatMessage, Conversation } from "@/types/chat";
import type { UploadedAsset } from "@/types/upload";

function createUserMessage(prompt: string, attachments: UploadedAsset[]): ChatMessage {
  return {
    id: `user_${Date.now()}`,
    role: "user",
    content: prompt,
    createdAt: new Date().toISOString(),
    status: "ready",
    attachments,
  };
}

function appendMessage(conversations: Conversation[], conversationId: string, message: ChatMessage) {
  return conversations.map((conversation) =>
    conversation.id === conversationId
      ? {
          ...conversation,
          updatedAt: new Date().toISOString(),
          messages: [...conversation.messages, message],
        }
      : conversation,
  );
}

export function useChat() {
  const { token, isReady, isAuthenticated } = useAuth();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [threadLoading, setThreadLoading] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const hydrateThread = useCallback(
    async (conversationId: string) => {
      if (!token || !isBackendConversationId(conversationId)) return;
      setThreadLoading(true);
      setError(null);
      try {
        const detail = await fetchConversationDetail(token, conversationId);
        setConversations((current) => current.map((c) => (c.id === conversationId ? detail : c)));
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unable to load conversation.");
      } finally {
        setThreadLoading(false);
      }
    },
    [token],
  );

  useEffect(() => {
    if (!isReady || !isAuthenticated) return;

    let cancelled = false;

    const load = async () => {
      setLoading(true);
      setError(null);

      try {
        const response = await fetchConversations(token);
        if (cancelled) return;
        setConversations(response.conversations);

        const storedId = uiStore.getActiveConversation();
        const resolvedId =
          response.conversations.find((item) => item.id === storedId)?.id ??
          response.conversations[0]?.id ??
          "";

        setActiveConversationId(resolvedId);

        if (token && resolvedId && isBackendConversationId(resolvedId)) {
          setThreadLoading(true);
          try {
            const detail = await fetchConversationDetail(token, resolvedId);
            if (cancelled) return;
            setConversations((current) => current.map((c) => (c.id === resolvedId ? detail : c)));
          } catch (err) {
            if (!cancelled) {
              setError(err instanceof Error ? err.message : "Unable to load conversation.");
            }
          } finally {
            if (!cancelled) setThreadLoading(false);
          }
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Unable to load conversations.");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    void load();
    return () => {
      cancelled = true;
    };
  }, [isReady, isAuthenticated, token]);

  useEffect(() => {
    if (activeConversationId) {
      uiStore.setActiveConversation(activeConversationId);
    }
  }, [activeConversationId]);

  const activeConversation = useMemo(
    () => conversations.find((conversation) => conversation.id === activeConversationId) ?? null,
    [conversations, activeConversationId],
  );

  const startNewChat = () => {
    const conversation = createConversationShell();
    setConversations((current) => [conversation, ...current]);
    setActiveConversationId(conversation.id);
    setError(null);
  };

  const selectConversation = (conversationId: string) => {
    setActiveConversationId(conversationId);
    setError(null);
    void hydrateThread(conversationId);
  };

  const sendPrompt = async (prompt: string, attachments: UploadedAsset[] = []) => {
    const trimmed = prompt.trim();
    if (!trimmed) return false;
    if (attachments.length === 0) {
      setError("Upload and attach at least one CSV or JSON file before running analysis.");
      return false;
    }

    let conversationId = activeConversationId;

    if (!conversationId) {
      const shell = createConversationShell(trimmed);
      conversationId = shell.id;
      setConversations((current) => [shell, ...current]);
      setActiveConversationId(shell.id);
    }

    const userMessage = createUserMessage(trimmed, attachments);
    setConversations((current) => appendMessage(current, conversationId, userMessage));
    setIsSubmitting(true);
    setError(null);

    try {
      const response = await submitChatPrompt(
        {
          conversationId,
          prompt: trimmed,
          attachmentIds: attachments.map((item) => item.id),
        },
        token,
      );

      const resolvedId = response.conversationId;

      if (token && isBackendConversationId(resolvedId)) {
        try {
          const detail = await fetchConversationDetail(token, resolvedId);
          setConversations((current) => {
            const rest = current.filter((c) => c.id !== conversationId && c.id !== detail.id);
            return [detail, ...rest];
          });
          setActiveConversationId(detail.id);
        } catch {
          setConversations((current) =>
            current.map((conversation) =>
              conversation.id === conversationId
                ? {
                    ...conversation,
                    id: resolvedId,
                    title:
                      conversation.messages.length <= 1 || conversation.title === "New analysis"
                        ? response.title
                        : conversation.title,
                    updatedAt: new Date().toISOString(),
                    mode: response.mode,
                    sourceLabel:
                      response.mode === "live"
                        ? "Connected backend"
                        : attachments.length > 0
                          ? "Uploaded dataset"
                          : conversation.sourceLabel,
                    messages: [...conversation.messages, response.message],
                  }
                : conversation,
            ),
          );
          setActiveConversationId(resolvedId);
        }
      } else {
        setConversations((current) =>
          current.map((conversation) =>
            conversation.id === conversationId
              ? {
                  ...conversation,
                  title:
                    conversation.messages.length === 0 || conversation.title === "New analysis"
                      ? response.title
                      : conversation.title,
                  updatedAt: new Date().toISOString(),
                  mode: response.mode,
                  sourceLabel:
                    response.mode === "live"
                      ? "Connected backend"
                      : attachments.length > 0
                        ? "Uploaded dataset"
                        : conversation.sourceLabel,
                  messages: [...conversation.messages, response.message],
                }
              : conversation,
          ),
        );
      }

      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to reach Planera.");
      return false;
    } finally {
      setIsSubmitting(false);
    }
  };

  return {
    conversations,
    activeConversation,
    activeConversationId,
    loading,
    threadLoading,
    isSubmitting,
    error,
    startNewChat,
    selectConversation,
    sendPrompt,
  };
}
