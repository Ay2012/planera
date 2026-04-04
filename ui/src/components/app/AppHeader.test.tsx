import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { AppHeader } from "@/components/app/AppHeader";

describe("AppHeader", () => {
  it("renders workspace status badges from props", () => {
    render(
      <AppHeader
        title="Revenue workspace"
        subtitle="Live answers with inspection details."
        uploadedLabel="Uploaded CSV"
        connectionLabel="Connected backend"
        connectionTone="accent"
        modeLabel="Live mode"
        modeTone="success"
        onToggleSidebar={vi.fn()}
      />,
    );

    expect(screen.getByRole("heading", { name: "Revenue workspace" })).toBeInTheDocument();
    expect(screen.getByText("Connected backend")).toBeInTheDocument();
    expect(screen.getByText("Live mode")).toBeInTheDocument();
    expect(screen.getByText("Uploaded CSV")).toBeInTheDocument();
  });
});
