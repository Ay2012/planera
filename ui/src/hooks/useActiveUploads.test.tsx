import { renderHook, waitFor } from "@testing-library/react";
import { act } from "react";
import { describe, expect, it } from "vitest";
import { useActiveUploads } from "@/hooks/useActiveUploads";
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

describe("useActiveUploads", () => {
  it("defaults all visible uploads to active", () => {
    const uploads = [createAsset("source_1", "orders.csv"), createAsset("source_2", "customers.csv")];
    const { result } = renderHook(({ items }) => useActiveUploads(items), {
      initialProps: { items: uploads },
    });

    expect(result.current.activeUploadIds).toEqual(["source_1", "source_2"]);
    expect(result.current.activeUploads.map((asset) => asset.id)).toEqual(["source_1", "source_2"]);
  });

  it("keeps removals but auto-adds newly uploaded files", async () => {
    const first = createAsset("source_1", "orders.csv");
    const second = createAsset("source_2", "customers.csv");
    const third = createAsset("source_3", "inventory.csv");
    const { result, rerender } = renderHook(({ items }) => useActiveUploads(items), {
      initialProps: { items: [first, second] },
    });

    act(() => {
      result.current.removeActiveUpload("source_1");
    });

    act(() => {
      rerender({ items: [first, second, third] });
    });

    await waitFor(() => {
      expect(result.current.activeUploadIds).toEqual(["source_2", "source_3"]);
      expect(result.current.activeUploads.map((asset) => asset.id)).toEqual(["source_2", "source_3"]);
    });
  });
});
