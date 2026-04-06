import { useEffect, useMemo, useRef, useState } from "react";
import type { UploadedAsset } from "@/types/upload";

function mergeActiveUploadIds(
  currentIds: string[],
  previousVisibleIds: string[],
  uploads: UploadedAsset[],
): string[] {
  const visibleIds = uploads.map((asset) => asset.id);
  const next = currentIds.filter((id) => visibleIds.includes(id));
  const newIds = visibleIds.filter((id) => !previousVisibleIds.includes(id));

  for (const id of newIds) {
    if (!next.includes(id)) {
      next.push(id);
    }
  }

  return next;
}

export function useActiveUploads(uploads: UploadedAsset[]) {
  const [activeUploadIds, setActiveUploadIds] = useState<string[]>([]);
  const previousVisibleIdsRef = useRef<string[]>([]);

  useEffect(() => {
    const previousVisibleIds = previousVisibleIdsRef.current;
    setActiveUploadIds((current) => {
      const next = mergeActiveUploadIds(current, previousVisibleIds, uploads);
      if (next.length === current.length && next.every((id, index) => id === current[index])) {
        return current;
      }
      return next;
    });
    previousVisibleIdsRef.current = uploads.map((asset) => asset.id);
  }, [uploads]);

  const activeUploads = useMemo(
    () => uploads.filter((asset) => activeUploadIds.includes(asset.id)),
    [activeUploadIds, uploads],
  );

  const removeActiveUpload = (assetId: string) => {
    setActiveUploadIds((current) => current.filter((id) => id !== assetId));
  };

  return {
    activeUploadIds,
    activeUploads,
    removeActiveUpload,
  };
}
