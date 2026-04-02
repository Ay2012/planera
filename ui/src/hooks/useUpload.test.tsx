import { renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

async function loadUseUpload(mode: "demo" | "hybrid" | "live") {
  vi.resetModules();
  vi.stubEnv("VITE_API_FALLBACK_MODE", mode);
  const module = await import("@/hooks/useUpload");
  return module.useUpload;
}

afterEach(() => {
  vi.unstubAllEnvs();
  vi.resetModules();
});

describe("useUpload", () => {
  it("seeds demo uploads only in demo-only mode", async () => {
    const useUpload = await loadUseUpload("demo");
    const { result } = renderHook(() => useUpload());

    expect(result.current.uploads.length).toBeGreaterThan(0);
    expect(result.current.latestUploadMode).toBe("demo");
  });

  it("starts with an empty upload list outside demo-only mode", async () => {
    const useUpload = await loadUseUpload("hybrid");
    const { result } = renderHook(() => useUpload());

    expect(result.current.uploads).toHaveLength(0);
    expect(result.current.latestUploadMode).toBeNull();
  });
});
