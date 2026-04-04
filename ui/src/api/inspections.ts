import { request } from "@/api/client";
import type { InspectionResponse } from "@/api/types";
import { shouldFallbackToDemo } from "@/config/env";
import { inspectionLibrary } from "@/data/mockInsights";
import { sleep } from "@/lib/utils";
import type { InspectionData } from "@/types/inspection";

const inspectionCache = new Map<string, InspectionData>();

export function cacheInspection(inspection: InspectionData) {
  inspectionCache.set(inspection.id, inspection);
}

/** Pass `accessToken` for persisted chat inspections (required after backend restart / cold cache). */
export async function fetchInspection(inspectionId: string, accessToken: string | null = null): Promise<InspectionResponse> {
  const cachedInspection = inspectionCache.get(inspectionId);
  if (cachedInspection) {
    return {
      inspection: cachedInspection,
      fallback: false,
    };
  }

  if (shouldFallbackToDemo) {
    await sleep(240);
    return {
      inspection: inspectionLibrary[inspectionId] ?? inspectionLibrary.inspect_pipeline_drop,
      fallback: true,
    };
  }

  const response = await request<InspectionResponse>(`/inspections/${inspectionId}`, {
    authToken: accessToken ?? undefined,
  });
  return { ...response, fallback: false };
}
