import { useEffect, useState } from "react";
import { deleteUpload as deleteUploadRequest, fetchUploads, uploadDataset } from "@/api/uploads";
import { useAuth } from "@/hooks/useAuth";
import type { UploadedAsset } from "@/types/upload";

export function useUpload() {
  const { token, isReady, isAuthenticated } = useAuth();
  const [uploads, setUploads] = useState<UploadedAsset[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [deletingUploadId, setDeletingUploadId] = useState<string | null>(null);
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

  const deleteUpload = async (sourceId: string) => {
    setDeletingUploadId(sourceId);
    setError(null);

    try {
      await deleteUploadRequest(sourceId, token);
      let remainingCount = 0;
      setUploads((current) => {
        const next = current.filter((asset) => asset.id !== sourceId);
        remainingCount = next.length;
        return next;
      });
      setLatestUploadMode(remainingCount > 0 ? "live" : null);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unable to delete file.";
      setError(message);
      throw err;
    } finally {
      setDeletingUploadId(null);
    }
  };

  return {
    uploads,
    isUploading,
    deletingUploadId,
    error,
    latestUploadMode,
    uploadFile,
    deleteUpload,
  };
}
