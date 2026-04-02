type FallbackMode = "hybrid" | "demo" | "live";

const fallbackMode = (import.meta.env.VITE_API_FALLBACK_MODE ?? "hybrid").toLowerCase();

export const env = {
  apiBaseUrl: (import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000").replace(/\/$/, ""),
  apiFallbackMode: (["hybrid", "demo", "live"].includes(fallbackMode) ? fallbackMode : "hybrid") as FallbackMode,
};

export const isDemoOnlyMode = env.apiFallbackMode === "demo";
export const shouldFallbackToDemo = env.apiFallbackMode !== "live";
