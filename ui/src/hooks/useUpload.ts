import { useState } from "react";
import { uploadDataset } from "@/api/uploads";
import { seededUploads } from "@/data/mockUploads";
import type { UploadedAsset } from "@/types/upload";

export function useUpload() {
  const [uploads, setUploads] = useState<UploadedAsset[]>(seededUploads);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const uploadFile = async (file: File) => {
    setIsUploading(true);
    setError(null);

    try {
      const response = await uploadDataset(file);
      setUploads((current) => [response.asset, ...current]);
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
    uploadFile,
  };
}
