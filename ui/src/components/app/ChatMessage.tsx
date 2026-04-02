import { Button } from "@/components/shared/Button";
import { Card } from "@/components/shared/Card";
import { InsightCard } from "@/components/app/InsightCard";
import { ResultTable } from "@/components/app/ResultTable";
import { SqlPreview } from "@/components/app/SqlPreview";
import { StatusBadge } from "@/components/app/StatusBadge";
import { formatTimestamp } from "@/lib/utils";
import type { ChatMessage as ChatMessageType } from "@/types/chat";
import type { InspectionTabId } from "@/types/inspection";

interface ChatMessageProps {
  message: ChatMessageType;
  onInspect: (inspectionId: string, preferredTab?: InspectionTabId) => void;
}

export function ChatMessage({ message, onInspect }: ChatMessageProps) {
  const isAssistant = message.role === "assistant";
  const payload = message.payload;
  const maxChartValue = payload?.chart?.length ? Math.max(...payload.chart.map((point) => point.value)) : 1;

  if (!isAssistant) {
    return (
      <div className="flex min-w-0 justify-end">
        <div className="w-full min-w-0 max-w-[720px] rounded-[24px] bg-ink px-5 py-4 text-sm leading-7 text-white shadow-card">
          <p>{message.content}</p>
          <p className="mt-2 text-xs text-white/70">{formatTimestamp(message.createdAt)}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-w-0 gap-3">
      <div className="mt-1 flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-accent text-sm font-semibold text-white shadow-card">
        P
      </div>
      <div className="min-w-0 flex-1 max-w-[860px] space-y-4">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-sm font-semibold text-ink">Planera</p>
            {payload?.verificationLabel ? (
              <StatusBadge label={payload.verificationLabel} tone={payload.verificationLabel === "Verified" ? "success" : "warning"} />
            ) : null}
            {payload?.executionLabel ? <StatusBadge label={payload.executionLabel} tone="accent" /> : null}
          </div>
          <p className="mt-3 text-[15px] leading-8 text-ink">{message.content}</p>
        </div>

        {payload?.details.length ? (
          <ul className="space-y-2 text-sm leading-7 text-muted">
            {payload.details.map((detail) => (
              <li key={detail} className="flex gap-3">
                <span className="mt-[11px] h-1.5 w-1.5 rounded-full bg-accent" />
                <span>{detail}</span>
              </li>
            ))}
          </ul>
        ) : null}

        {payload?.metrics.length ? (
          <div className="grid min-w-0 gap-3 sm:grid-cols-3">
            {payload.metrics.map((metric) => (
              <Card key={metric.id} className="p-4">
                <p className="text-xs font-medium uppercase tracking-[0.14em] text-muted">{metric.label}</p>
                <p className="mt-2 text-xl font-semibold text-ink">{metric.value}</p>
                <p className="mt-1 text-sm text-muted">{metric.change}</p>
              </Card>
            ))}
          </div>
        ) : null}

        {payload?.insights.length ? (
          <div className="grid min-w-0 gap-3 md:grid-cols-2">
            {payload.insights.map((insight) => (
              <InsightCard key={insight.id} title={insight.title} body={insight.body} tone={insight.tone} />
            ))}
          </div>
        ) : null}

        {payload?.chart?.length ? (
          <Card className="min-w-0 p-4">
            <div className="flex items-center justify-between">
              <p className="text-sm font-semibold text-ink">Signal view</p>
              {payload.confidence ? <p className="text-xs text-muted">{Math.round(payload.confidence * 100)}% confidence</p> : null}
            </div>
            <div className="mt-4 space-y-3">
              {payload.chart.map((point) => (
                <div key={point.label} className="grid min-w-0 grid-cols-[100px_minmax(0,1fr)_auto] items-center gap-3">
                  <span className="text-sm text-muted">{point.label}</span>
                  <div className="h-2 rounded-full bg-surface">
                    <div
                      className="h-2 rounded-full bg-accent"
                      style={{ width: `${Math.max((point.value / maxChartValue) * 100, 14)}%` }}
                    />
                  </div>
                  <span className="text-sm font-medium text-ink">{point.value}</span>
                </div>
              ))}
            </div>
          </Card>
        ) : null}

        {payload?.previewTable ? <ResultTable title="Result preview" table={payload.previewTable} /> : null}

        {payload?.sqlPreview ? <SqlPreview code={payload.sqlPreview} compact /> : null}

        {payload?.recommendations.length ? (
          <Card className="min-w-0 p-4">
            <p className="text-sm font-semibold text-ink">Recommended next actions</p>
            <div className="mt-3 space-y-2 text-sm leading-7 text-muted">
              {payload.recommendations.map((recommendation) => (
                <div key={recommendation} className="flex gap-3">
                  <span className="mt-[11px] h-1.5 w-1.5 rounded-full bg-accent" />
                  <span>{recommendation}</span>
                </div>
              ))}
            </div>
          </Card>
        ) : null}

        {payload?.inspectionId ? (
          <div className="flex flex-wrap items-center gap-3">
            <Button onClick={() => onInspect(payload.inspectionId!)}>Inspect SQL</Button>
            <Button variant="secondary" onClick={() => onInspect(payload.inspectionId!, "results")}>
              Open execution detail
            </Button>
          </div>
        ) : null}
      </div>
    </div>
  );
}
