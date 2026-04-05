import { useEffect, useState } from "react";
import { fetchUploads, uploadDataset } from "@/api/uploads";
import { useAuth } from "@/hooks/useAuth";
import type { UploadedAsset } from "@/types/upload";

export function useUpload() {
  const { token, isReady, isAuthenticated } = useAuth();
  const [uploads, setUploads] = useState<UploadedAsset[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [latestUploadMode, setLatestUploadMode] = useState<"live" | "demo" | null>(null);

  useEffect(() => {
    if (!isReady) return;

    if (!isAuthenticated || !token) {
      setUploads([]);
      setLatestUploadMode(null);
      setError(null);
      return;
    }

    let cancelled = false;

    const load = async () => {
      setError(null);
      try {
        const nextUploads = await fetchUploads(token);
        if (cancelled) return;
        setUploads(nextUploads);
        setLatestUploadMode(nextUploads.length > 0 ? "live" : null);
      } catch (err) {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "Unable to load uploads.");
      }
    };

    void load();
    return () => {
      cancelled = true;
    };
  }, [isAuthenticated, isReady, token]);

  const uploadFile = async (file: File) => {
    setIsUploading(true);
    setError(null);

    try {
      const response = await uploadDataset(file, token);
      setUploads((current) => [response.asset, ...current.filter((asset) => asset.id !== response.asset.id)]);
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
