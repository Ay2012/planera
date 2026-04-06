export const UPLOAD_ACCEPT = ".csv,.json,application/json,text/csv";

export function isSupportedUploadFile(file: Pick<File, "name">): boolean {
  const normalized = file.name.trim().toLowerCase();
  return normalized.endsWith(".csv") || normalized.endsWith(".json");
}
