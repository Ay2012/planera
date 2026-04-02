import { useState } from "react";
import { Card } from "@/components/shared/Card";
import { Button } from "@/components/shared/Button";

interface SqlPreviewProps {
  code: string;
  compact?: boolean;
}

export function SqlPreview({ code, compact = false }: SqlPreviewProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1200);
  };

  return (
    <Card className="max-w-full min-w-0 overflow-hidden">
      <div className="flex min-w-0 flex-wrap items-center justify-between gap-3 border-b border-line px-4 py-3">
        <div className="min-w-0">
          <p className="text-sm font-semibold text-ink">Generated query</p>
          <p className="text-xs text-muted">Readable SQL surfaced directly in the workspace.</p>
        </div>
        <Button variant="secondary" size="sm" onClick={handleCopy}>
          {copied ? "Copied" : "Copy SQL"}
        </Button>
      </div>
      <pre className={`max-w-full overflow-x-auto bg-[#111417] p-4 font-mono text-xs leading-6 text-[#e6efe9] ${compact ? "max-h-52" : ""}`}>
        <code>{code}</code>
      </pre>
    </Card>
  );
}
