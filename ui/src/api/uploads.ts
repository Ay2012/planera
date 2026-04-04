import { request } from "@/api/client";
import type { UploadResponse } from "@/api/types";
import { createUploadedAsset } from "@/data/mockUploads";
import { shouldFallbackToDemo } from "@/config/env";
import { sleep } from "@/lib/utils";

export async function uploadDataset(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append("file", file);

  try {
    const response = await request<UploadResponse>("/uploads", {
      method: "POST",
      body: formData,
    });
    return { ...response, fallback: false };
  } catch (error) {
    if (!shouldFallbackToDemo) throw error;
    await sleep(480);
    return {
      asset: {
        ...createUploadedAsset(file),
        source: "Demo fallback",
        status: "verified",
        rows: 12840,
        columns: 9,
        summary: "Demo fallback profiling completed. The uploaded file is shown with generated preview statistics.",
      },
      fallback: true,
    };
  }
}
