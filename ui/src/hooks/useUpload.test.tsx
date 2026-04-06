import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { UploadedAsset } from "@/types/upload";

function createAsset(id: string, name: string): UploadedAsset {
  return {
    id,
    name,
    type: "CSV",
    source: "Workspace upload",
    sizeLabel: "1.0 KB",
    uploadedAt: new Date().toISOString(),
    status: "verified",
  };
}

async function loadUseUpload(options?: {
  isReady?: boolean;
  isAuthenticated?: boolean;
  token?: string | null;
  fetchedUploads?: UploadedAsset[];
}) {
  vi.resetModules();
  const fetchUploads = vi.fn().mockResolvedValue(options?.fetchedUploads ?? []);
  const uploadDataset = vi.fn().mockResolvedValue({
    asset: createAsset("source_uploaded", "orders.csv"),
    fallback: false,
  });
  const deleteUpload = vi.fn().mockResolvedValue(undefined);

  vi.doMock("@/hooks/useAuth", () => ({
    useAuth: () => ({
      user:
        options?.isAuthenticated === false
          ? null
          : { id: 1, email: "test@example.com", display_name: null, created_at: new Date().toISOString() },
      token: options?.token ?? "token_123",
      isReady: options?.isReady ?? true,
      isAuthenticated: options?.isAuthenticated ?? true,
      login: vi.fn(),
      signUp: vi.fn(),
      logout: vi.fn(),
    }),
  }));
  vi.doMock("@/api/uploads", () => ({
    fetchUploads,
    uploadDataset,
    deleteUpload,
  }));

  const module = await import("@/hooks/useUpload");
  return { useUpload: module.useUpload, fetchUploads, uploadDataset, deleteUpload };
}

afterEach(() => {
  vi.resetModules();
  vi.clearAllMocks();
});

describe("useUpload", () => {
  it("stays empty when the user is not authenticated", async () => {
    const { useUpload, fetchUploads } = await loadUseUpload({ isAuthenticated: false, token: null });
    const { result } = renderHook(() => useUpload());

    expect(result.current.uploads).toHaveLength(0);
    expect(result.current.latestUploadMode).toBeNull();
    expect(fetchUploads).not.toHaveBeenCalled();
  });

  it("hydrates uploads for the signed-in user", async () => {
    const fetchedUploads = [createAsset("source_1", "orders.csv"), createAsset("source_2", "customers.csv")];
    const { useUpload, fetchUploads } = await loadUseUpload({ fetchedUploads });
    const { result } = renderHook(() => useUpload());

    await waitFor(() => {
      expect(result.current.uploads).toHaveLength(2);
    });

    expect(fetchUploads).toHaveBeenCalledWith("token_123");
    expect(result.current.latestUploadMode).toBe("live");
  });

  it("prepends a newly uploaded file", async () => {
    const fetchedUploads = [createAsset("source_existing", "customers.csv")];
    const uploadedAsset = createAsset("source_uploaded", "orders.csv");
    const { useUpload, uploadDataset } = await loadUseUpload({ fetchedUploads });
    uploadDataset.mockResolvedValue({ asset: uploadedAsset, fallback: false });

    const { result } = renderHook(() => useUpload());

    await waitFor(() => {
      expect(result.current.uploads).toHaveLength(1);
    });

    await act(async () => {
      await result.current.uploadFile(new File(["order_id\n1"], "orders.csv", { type: "text/csv" }));
    });

    expect(uploadDataset).toHaveBeenCalled();
    expect(result.current.uploads.map((asset) => asset.id)).toEqual(["source_uploaded", "source_existing"]);
    expect(result.current.latestUploadMode).toBe("live");
  });

  it("removes a deleted file from the upload list", async () => {
    const fetchedUploads = [createAsset("source_existing", "customers.csv"), createAsset("source_delete", "orders.csv")];
    const { useUpload, deleteUpload } = await loadUseUpload({ fetchedUploads });
    const { result } = renderHook(() => useUpload());

    await waitFor(() => {
      expect(result.current.uploads).toHaveLength(2);
    });

    await act(async () => {
      await result.current.deleteUpload("source_delete");
    });

    expect(deleteUpload).toHaveBeenCalledWith("source_delete", "token_123");
    expect(result.current.uploads.map((asset) => asset.id)).toEqual(["source_existing"]);
  });
});
