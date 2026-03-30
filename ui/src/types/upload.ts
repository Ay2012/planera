export type UploadStatus = "uploaded" | "profiling" | "verified" | "error";

export interface UploadedAsset {
  id: string;
  name: string;
  type: string;
  source: string;
  sizeLabel: string;
  uploadedAt: string;
  status: UploadStatus;
  rows?: number;
  columns?: number;
  summary?: string;
}
