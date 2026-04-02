import { useRef } from "react";
import { Button } from "@/components/shared/Button";
import { Textarea } from "@/components/shared/Textarea";
import { PromptChips } from "@/components/app/PromptChips";
import { Spinner } from "@/components/shared/Spinner";
import type { UploadedAsset } from "@/types/upload";

interface ChatInputProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  onPickPrompt: (prompt: string) => void;
  onUpload: (file: File) => void;
  onRemoveAttachment: (assetId: string) => void;
  attachments: UploadedAsset[];
  isSubmitting: boolean;
  isUploading: boolean;
}

export function ChatInput({
  value,
  onChange,
  onSubmit,
  onPickPrompt,
  onUpload,
  onRemoveAttachment,
  attachments,
  isSubmitting,
  isUploading,
}: ChatInputProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);

  return (
    <div className="border-t border-line/80 bg-canvas/90 px-4 py-4 backdrop-blur sm:px-6">
      <div className="mx-auto w-full min-w-0 max-w-4xl space-y-4">
        <PromptChips onPick={onPickPrompt} />
        {attachments.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            {attachments.map((asset) => (
              <span key={asset.id} className="inline-flex items-center gap-2 rounded-full border border-line bg-panel px-3 py-2 text-xs text-muted">
                {asset.name}
                <button type="button" onClick={() => onRemoveAttachment(asset.id)} className="text-ink">
                  ×
                </button>
              </span>
            ))}
          </div>
        ) : null}
        <div className="min-w-0 rounded-[28px] border border-line bg-panel p-3 shadow-card">
          <Textarea
            value={value}
            onChange={(event) => onChange(event.target.value)}
            placeholder="Ask a question about your data. Planera will analyze, explain, and show the underlying work."
            className="min-h-[120px] resize-none border-none p-2 shadow-none focus:border-transparent"
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                onSubmit();
              }
            }}
          />
          <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
            <div className="flex min-w-0 flex-wrap items-center gap-2">
              <input
                ref={fileInputRef}
                type="file"
                className="hidden"
                onChange={(event) => {
                  const file = event.target.files?.[0];
                  if (file) {
                    onUpload(file);
                    event.currentTarget.value = "";
                  }
                }}
              />
              <Button variant="secondary" size="sm" onClick={() => fileInputRef.current?.click()}>
                {isUploading ? <Spinner className="h-4 w-4" /> : null}
                Attach file
              </Button>
              <span className="min-w-0 text-xs text-muted">CSV, TSV, SQL exports, or connected data sources</span>
            </div>
            <Button onClick={onSubmit} disabled={isSubmitting || value.trim().length === 0}>
              {isSubmitting ? <Spinner className="h-4 w-4 border-white/30 border-t-white" /> : null}
              Send
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
