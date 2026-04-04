import { useState } from "react";
import { uploadDataset } from "@/api/uploads";
import { isDemoOnlyMode } from "@/config/env";
import { seededUploads } from "@/data/mockUploads";
import type { UploadedAsset } from "@/types/upload";

export function useUpload() {
  const [uploads, setUploads] = useState<UploadedAsset[]>(() => (isDemoOnlyMode ? seededUploads : []));
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [latestUploadMode, setLatestUploadMode] = useState<"live" | "demo" | null>(() =>
    isDemoOnlyMode && seededUploads.length > 0 ? "demo" : null,
  );

  const uploadFile = async (file: File) => {
    setIsUploading(true);
    setError(null);

    try {
      const response = await uploadDataset(file);
      setUploads((current) => [response.asset, ...current]);
      setLatestUploadMode(response.fallback ? "demo" : "live");
      return response.asset;
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unable to upload file.";
      setError(message);
      throw err;
    } finally {
      setIsUploading(false);
    }
  };

  return {
    uploads,
    isUploading,
    error,
    latestUploadMode,
    uploadFile,
  };
}
