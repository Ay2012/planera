import { useEffect, useMemo, useState } from "react";
import { createConversationShell, fetchConversations, submitChatPrompt } from "@/api/chat";
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
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      setError(null);

      try {
        const response = await fetchConversations();
        setConversations(response.conversations);

        const storedId = uiStore.getActiveConversation();
        const nextActiveId = response.conversations.find((item) => item.id === storedId)?.id ?? response.conversations[0]?.id ?? "";
        setActiveConversationId(nextActiveId);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unable to load conversations.");
      } finally {
        setLoading(false);
      }
    };

    void load();
  }, []);

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
  };

  const sendPrompt = async (prompt: string, attachments: UploadedAsset[] = []) => {
    const trimmed = prompt.trim();
    if (!trimmed) return false;

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
      const response = await submitChatPrompt({
        conversationId,
        prompt: trimmed,
        attachmentIds: attachments.map((item) => item.id),
      });

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
    isSubmitting,
    error,
    startNewChat,
    selectConversation,
    sendPrompt,
  };
}
