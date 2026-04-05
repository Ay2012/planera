import { ApiError, request } from "@/api/client";
import type { UploadResponse } from "@/api/types";
import { isSupportedUploadFile } from "@/lib/uploads";

export async function uploadDataset(file: File): Promise<UploadResponse> {
  if (!isSupportedUploadFile(file)) {
    throw new ApiError("Only CSV and JSON files are supported.");
  }

  const formData = new FormData();
  formData.append("file", file);

  const response = await request<UploadResponse>("/uploads", {
    method: "POST",
    body: formData,
  });
  return { ...response, fallback: false };
}
