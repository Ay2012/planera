import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { UploadsPanel } from "@/components/app/UploadsPanel";

afterEach(() => {
  cleanup();
});

describe("UploadsPanel", () => {
  it("renders a file picker restricted to csv and json", () => {
    render(
      <UploadsPanel
        uploads={[]}
        error={null}
        isUploading={false}
        deletingUploadId={null}
        onUpload={vi.fn()}
        onDelete={vi.fn()}
      />,
    );

    expect(screen.getByRole("button", { name: "Upload file" })).toBeInTheDocument();
    expect(screen.getByTestId("uploads-panel-file-input")).toHaveAttribute(
      "accept",
      ".csv,.json,application/json,text/csv",
    );
  });

  it("forwards selected files to the upload callback", () => {
    const onUpload = vi.fn();
    render(
      <UploadsPanel
        uploads={[]}
        error={null}
        isUploading={false}
        deletingUploadId={null}
        onUpload={onUpload}
        onDelete={vi.fn()}
      />,
    );

    const input = screen.getByTestId("uploads-panel-file-input");
    const file = new File(["order_id,total\n1,25"], "orders.csv", { type: "text/csv" });

    fireEvent.change(input, { target: { files: [file] } });

    expect(onUpload).toHaveBeenCalledWith(file);
  });

  it("renders a delete action for each uploaded file", () => {
    const onDelete = vi.fn();
    render(
      <UploadsPanel
        uploads={[
          {
            id: "source_1",
            name: "orders.json",
            type: "JSON",
            source: "Workspace upload",
            sizeLabel: "1.0 KB",
            uploadedAt: new Date().toISOString(),
            status: "verified",
          },
        ]}
        error={null}
        isUploading={false}
        deletingUploadId={null}
        onUpload={vi.fn()}
        onDelete={onDelete}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Delete orders.json" }));

    expect(onDelete).toHaveBeenCalledWith("source_1");
  });
});
