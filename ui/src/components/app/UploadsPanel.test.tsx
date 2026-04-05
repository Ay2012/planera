import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { UploadsPanel } from "@/components/app/UploadsPanel";

afterEach(() => {
  cleanup();
});

describe("UploadsPanel", () => {
  it("renders a file picker restricted to csv and json", () => {
    render(<UploadsPanel uploads={[]} error={null} isUploading={false} onUpload={vi.fn()} />);

    expect(screen.getByRole("button", { name: "Upload file" })).toBeInTheDocument();
    expect(screen.getByTestId("uploads-panel-file-input")).toHaveAttribute(
      "accept",
      ".csv,.json,application/json,text/csv",
    );
  });

  it("forwards selected files to the upload callback", () => {
    const onUpload = vi.fn();
    render(<UploadsPanel uploads={[]} error={null} isUploading={false} onUpload={onUpload} />);

    const input = screen.getByTestId("uploads-panel-file-input");
    const file = new File(["order_id,total\n1,25"], "orders.csv", { type: "text/csv" });

    fireEvent.change(input, { target: { files: [file] } });

    expect(onUpload).toHaveBeenCalledWith(file);
  });
});
