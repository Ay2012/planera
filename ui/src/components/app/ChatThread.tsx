import { useEffect, useRef } from "react";
import { ChatMessage } from "@/components/app/ChatMessage";
import { EmptyState } from "@/components/shared/EmptyState";
import { Spinner } from "@/components/shared/Spinner";
import type { ChatMessage as ChatMessageType } from "@/types/chat";
import type { InspectionTabId } from "@/types/inspection";

interface ChatThreadProps {
  messages: ChatMessageType[];
  isSubmitting: boolean;
  onInspect: (inspectionId: string, preferredTab?: InspectionTabId) => void;
}

export function ChatThread({ messages, isSubmitting, onInspect }: ChatThreadProps) {
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isSubmitting]);

  if (!messages.length) {
    return (
      <EmptyState
        title="Start a fresh analysis"
        description="Ask Planera a business question, upload a dataset, or generate a query path to begin. The workspace will keep the conversation readable while preserving the technical details underneath."
      />
    );
  }

  return (
    <div className="min-w-0 space-y-8">
      {messages.map((message) => (
        <ChatMessage key={message.id} message={message} onInspect={onInspect} />
      ))}
      {isSubmitting ? (
        <div className="flex gap-3">
          <div className="mt-1 flex h-10 w-10 items-center justify-center rounded-2xl bg-accent text-sm font-semibold text-white">P</div>
          <div className="rounded-[24px] border border-line bg-panel px-5 py-4 text-sm text-muted shadow-card">
            <div className="flex items-center gap-3">
              <Spinner />
              Planera is running the analysis and preparing an inspection trail.
            </div>
          </div>
        </div>
      ) : null}
      <div ref={bottomRef} />
    </div>
  );
}
