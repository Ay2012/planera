import { Card } from "@/components/shared/Card";
import { StatusBadge } from "@/components/app/StatusBadge";
import { formatRelativeTime } from "@/lib/utils";
import type { UploadedAsset } from "@/types/upload";

interface UploadCardProps {
  asset: UploadedAsset;
  onDelete?: (assetId: string) => void;
  isDeleting?: boolean;
}

export function UploadCard({ asset, onDelete, isDeleting = false }: UploadCardProps) {
  const tone = asset.status === "verified" ? "success" : asset.status === "error" ? "danger" : "accent";

  return (
    <Card className="min-w-0 p-4">
      <div className="flex min-w-0 items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-ink">{asset.name}</p>
          <p className="mt-1 text-xs text-muted">
            {asset.type} • {asset.sizeLabel} • {formatRelativeTime(asset.uploadedAt)}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <StatusBadge label={asset.status} tone={tone} />
          {onDelete ? (
            <button
              type="button"
              aria-label={`Delete ${asset.name}`}
              disabled={isDeleting}
              onClick={() => onDelete(asset.id)}
              className="inline-flex h-8 w-8 items-center justify-center rounded-full border border-line bg-panel text-muted transition hover:text-ink disabled:cursor-not-allowed disabled:opacity-60"
            >
              <svg className="h-4 w-4" viewBox="0 0 16 16" fill="none">
                <path d="M5.5 5.5V11M8 5.5V11M10.5 5.5V11M3.5 4H12.5M6 4V3.25C6 2.84 6.34 2.5 6.75 2.5H9.25C9.66 2.5 10 2.84 10 3.25V4M4.5 4V12C4.5 12.83 5.17 13.5 6 13.5H10C10.83 13.5 11.5 12.83 11.5 12V4" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </button>
          ) : null}
        </div>
      </div>
      {asset.summary ? <p className="mt-3 text-sm leading-6 text-muted">{asset.summary}</p> : null}
      {(asset.rows || asset.columns) && (
        <div className="mt-4 flex flex-wrap gap-2 text-xs text-muted">
          {asset.rows ? <span className="rounded-full bg-surface px-3 py-1">{asset.rows.toLocaleString()} rows</span> : null}
          {asset.columns ? <span className="rounded-full bg-surface px-3 py-1">{asset.columns} columns</span> : null}
          {asset.relationCount ? <span className="rounded-full bg-surface px-3 py-1">{asset.relationCount} relations</span> : null}
        </div>
      )}
      {asset.primaryRelationName ? (
        <p className="mt-3 text-xs text-muted">Primary relation: {asset.primaryRelationName}</p>
      ) : null}
    </Card>
  );
}
