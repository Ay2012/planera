import type { UploadedAsset } from "@/types/upload";
import { bytesToSize, shortId } from "@/lib/utils";

export const seededUploads: UploadedAsset[] = [
  {
    id: "upload_finance_q2",
    name: "finance_forecast_q2.csv",
    type: "CSV",
    source: "Workspace upload",
    sizeLabel: "2.4 MB",
    uploadedAt: "2026-03-25T09:12:00.000Z",
    status: "verified",
    rows: 18240,
    columns: 12,
    summary: "Quarterly revenue, margin, and plan variance by region and product line.",
  },
  {
    id: "upload_product_health",
    name: "product_health.tsv",
    type: "TSV",
    source: "Workspace upload",
    sizeLabel: "864 KB",
    uploadedAt: "2026-03-24T18:40:00.000Z",
    status: "profiling",
    rows: 6420,
    columns: 8,
    summary: "Engagement, retention, and activation metrics across product surfaces.",
  },
];

export function createUploadedAsset(file: File): UploadedAsset {
  return {
    id: shortId("upload"),
    name: file.name,
    type: file.name.split(".").pop()?.toUpperCase() ?? "FILE",
    source: "Workspace upload",
    sizeLabel: bytesToSize(file.size),
    uploadedAt: new Date().toISOString(),
    status: "uploaded",
    summary: "Freshly uploaded dataset ready for profiling and analysis.",
  };
}
