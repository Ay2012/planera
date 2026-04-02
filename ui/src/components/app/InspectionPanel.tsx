import { Drawer } from "@/components/shared/Drawer";
import { ErrorState } from "@/components/shared/ErrorState";
import { Spinner } from "@/components/shared/Spinner";
import { Button } from "@/components/shared/Button";
import { SqlPreview } from "@/components/app/SqlPreview";
import { ResultTable } from "@/components/app/ResultTable";
import { ValidationSummary } from "@/components/app/ValidationSummary";
import { InspectionTabs } from "@/components/app/InspectionTabs";
import { StatusBadge } from "@/components/app/StatusBadge";
import { Card } from "@/components/shared/Card";
import { formatTimestamp } from "@/lib/utils";
import type { InspectionData, InspectionTabId } from "@/types/inspection";

interface InspectionPanelProps {
  open: boolean;
  loading: boolean;
  error: string | null;
  inspection: InspectionData | null;
  activeTab: InspectionTabId;
  maximized: boolean;
  onClose: () => void;
  onToggleMaximized: () => void;
  onTabChange: (tab: InspectionTabId) => void;
}

function TraceList({ inspection }: { inspection: InspectionData }) {
  const badgeForStatus = (status: InspectionData["trace"][number]["status"]) => {
    if (status === "error") return { label: "Failed", tone: "danger" as const };
    if (status === "warning") return { label: "Review", tone: "warning" as const };
    if (status === "running") return { label: "Running", tone: "accent" as const };
    return { label: "Complete", tone: "success" as const };
  };

  return (
    <div className="space-y-3">
      {inspection.trace.map((step) => (
        <Card key={step.id} className="p-4">
          <div className="flex items-start justify-between gap-4">
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <p className="text-sm font-semibold text-ink">{step.label}</p>
                <StatusBadge label={badgeForStatus(step.status).label} tone={badgeForStatus(step.status).tone} />
              </div>
              <p className="mt-2 text-sm leading-6 text-muted">{step.description}</p>
              <p className="mt-3 text-sm leading-6 text-ink">{step.detail}</p>
            </div>
            <span className="text-xs uppercase tracking-[0.14em] text-muted">{step.durationLabel}</span>
          </div>
        </Card>
      ))}
    </div>
  );
}

export function InspectionPanel({
  open,
  loading,
  error,
  inspection,
  activeTab,
  maximized,
  onClose,
  onToggleMaximized,
  onTabChange,
}: InspectionPanelProps) {
  return (
    <Drawer
      open={open}
      onClose={onClose}
      title={inspection?.title ?? "Inspection"}
      subtitle="LeetCode-style execution feedback adapted for analytics workflows."
      maximized={maximized}
      actions={
        <Button variant="secondary" size="sm" onClick={onToggleMaximized}>
          {maximized ? "Collapse" : "Expand"}
        </Button>
      }
    >
      {loading ? (
        <div className="flex h-full min-h-[420px] items-center justify-center">
          <div className="flex items-center gap-3 rounded-full border border-line bg-surface px-4 py-3 text-sm text-muted">
            <Spinner />
            Loading inspection data
          </div>
        </div>
      ) : null}

      {!loading && error ? (
        <div className="p-5">
          <ErrorState title="Inspection unavailable" description={error} />
        </div>
      ) : null}

      {!loading && !error && inspection ? (
        <>
          <div className="border-b border-line/80 px-5 py-4">
            <div className="flex flex-wrap items-center gap-2">
              <StatusBadge label={inspection.status === "valid" ? "Query valid" : inspection.status === "warning" ? "Needs review" : "Issue"} tone={inspection.status === "valid" ? "success" : inspection.status === "warning" ? "warning" : "danger"} />
              <StatusBadge label={inspection.verified ? "Verified" : "Partial verification"} tone={inspection.verified ? "success" : "warning"} />
              <StatusBadge label={inspection.dataSource} tone="accent" />
            </div>
            <p className="mt-3 text-sm leading-6 text-muted">
              {inspection.queryType} on {inspection.engine} • {inspection.rowsReturned} rows • updated {formatTimestamp(inspection.lastUpdated)}
            </p>
            <div className="mt-4 flex flex-wrap gap-2">
              {inspection.filters.map((filter) => (
                <span key={filter} className="rounded-full border border-line bg-surface px-3 py-1 text-xs text-muted">
                  {filter}
                </span>
              ))}
            </div>
          </div>

          <InspectionTabs inspection={inspection} activeTab={activeTab} onChange={onTabChange} />

          <div className="space-y-5 p-5">
            {activeTab === "sql" ? (
              <>
                <SqlPreview code={inspection.query} />
                <Card className="p-4">
                  <p className="text-sm font-semibold text-ink">Result metadata</p>
                  <div className="mt-4 grid gap-3 sm:grid-cols-2">
                    {inspection.metadata.map((item) => (
                      <div key={item.label} className="rounded-2xl bg-surface px-4 py-3">
                        <p className="text-xs uppercase tracking-[0.14em] text-muted">{item.label}</p>
                        <p className="mt-2 text-sm font-semibold text-ink">{item.value}</p>
                      </div>
                    ))}
                  </div>
                </Card>
              </>
            ) : null}

            {activeTab === "results" ? (
              <>
                <ResultTable title="Executed result set" table={inspection.results} />
                <Card className="p-4">
                  <p className="text-sm font-semibold text-ink">Execution detail</p>
                  <div className="mt-4 grid gap-3 sm:grid-cols-2">
                    <div className="rounded-2xl bg-surface px-4 py-3">
                      <p className="text-xs uppercase tracking-[0.14em] text-muted">Data source</p>
                      <p className="mt-2 text-sm font-semibold text-ink">{inspection.dataSource}</p>
                    </div>
                    <div className="rounded-2xl bg-surface px-4 py-3">
                      <p className="text-xs uppercase tracking-[0.14em] text-muted">Runtime</p>
                      <p className="mt-2 text-sm font-semibold text-ink">
                        {inspection.runtimeMs == null ? "Not reported by backend" : `${inspection.runtimeMs} ms`}
                      </p>
                    </div>
                  </div>
                </Card>
              </>
            ) : null}

            {activeTab === "trace" ? <TraceList inspection={inspection} /> : null}

            {activeTab === "validation" ? (
              <>
                <ValidationSummary items={inspection.validation} />
                <Card className="p-4">
                  <p className="text-sm font-semibold text-ink">Inspection metadata</p>
                  <div className="mt-4 grid gap-3 sm:grid-cols-2">
                    <div className="rounded-2xl bg-surface px-4 py-3">
                      <p className="text-xs uppercase tracking-[0.14em] text-muted">Confidence</p>
                      <p className="mt-2 text-sm font-semibold text-ink">{Math.round(inspection.confidence * 100)}%</p>
                    </div>
                    <div className="rounded-2xl bg-surface px-4 py-3">
                      <p className="text-xs uppercase tracking-[0.14em] text-muted">Verification</p>
                      <p className="mt-2 text-sm font-semibold text-ink">{inspection.verified ? "Verified" : "Needs analyst review"}</p>
                    </div>
                  </div>
                </Card>
              </>
            ) : null}
          </div>
        </>
      ) : null}
    </Drawer>
  );
}
