import { Card } from "@/components/shared/Card";
import { StatusBadge } from "@/components/app/StatusBadge";
import { formatRelativeTime } from "@/lib/utils";
import type { UploadedAsset } from "@/types/upload";

interface UploadCardProps {
  asset: UploadedAsset;
}

export function UploadCard({ asset }: UploadCardProps) {
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
        <StatusBadge label={asset.status} tone={tone} />
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
