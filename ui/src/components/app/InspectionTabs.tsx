import { Tabs, type TabDefinition } from "@/components/shared/Tabs";
import type { InspectionData, InspectionTabId } from "@/types/inspection";
import { formatNumber, formatTimestamp } from "@/lib/utils";

interface InspectionTabsProps {
  inspection: InspectionData;
  activeTab: InspectionTabId;
  onChange: (tab: InspectionTabId) => void;
}

const tabs: TabDefinition<InspectionTabId>[] = [
  { id: "sql", label: "SQL" },
  { id: "results", label: "Results" },
  { id: "trace", label: "Trace" },
  { id: "validation", label: "Validation" },
];

export function InspectionTabs({ inspection, activeTab, onChange }: InspectionTabsProps) {
  return (
    <div className="border-b border-line/80 px-5 py-4">
      <div className="mb-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <div className="rounded-2xl bg-surface px-4 py-3">
          <p className="text-xs font-medium uppercase tracking-[0.14em] text-muted">Rows returned</p>
          <p className="mt-2 text-lg font-semibold text-ink">{formatNumber(inspection.rowsReturned)}</p>
        </div>
        <div className="rounded-2xl bg-surface px-4 py-3">
          <p className="text-xs font-medium uppercase tracking-[0.14em] text-muted">Runtime</p>
          <p className="mt-2 text-lg font-semibold text-ink">{inspection.runtimeMs == null ? "Not reported" : `${inspection.runtimeMs} ms`}</p>
        </div>
        <div className="rounded-2xl bg-surface px-4 py-3">
          <p className="text-xs font-medium uppercase tracking-[0.14em] text-muted">Confidence</p>
          <p className="mt-2 text-lg font-semibold text-ink">{Math.round(inspection.confidence * 100)}%</p>
        </div>
        <div className="rounded-2xl bg-surface px-4 py-3">
          <p className="text-xs font-medium uppercase tracking-[0.14em] text-muted">Last updated</p>
          <p className="mt-2 text-sm font-semibold text-ink">{formatTimestamp(inspection.lastUpdated)}</p>
        </div>
      </div>
      <Tabs tabs={tabs} activeTab={activeTab} onChange={onChange} />
    </div>
  );
}
