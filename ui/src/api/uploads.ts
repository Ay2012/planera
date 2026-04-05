import { ApiError, requestWithAuth } from "@/api/client";
import type { UploadResponse } from "@/api/types";
import type { UploadedAsset } from "@/types/upload";
import { isSupportedUploadFile } from "@/lib/uploads";

export async function fetchUploads(accessToken: string | null): Promise<UploadedAsset[]> {
  if (!accessToken) {
    throw new ApiError("Not authenticated.");
  }

  return requestWithAuth<UploadedAsset[]>("/uploads", accessToken);
}


export async function uploadDataset(file: File, accessToken: string | null): Promise<UploadResponse> {
  if (!isSupportedUploadFile(file)) {
    throw new ApiError("Only CSV and JSON files are supported.");
  }
  if (!accessToken) {
    throw new ApiError("Not authenticated.");
  }

  const formData = new FormData();
  formData.append("file", file);

  const response = await requestWithAuth<UploadResponse>("/uploads", accessToken, {
    method: "POST",
    body: formData,
  });
  return { ...response, fallback: false };
}
