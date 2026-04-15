import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ChatInput } from "@/components/app/ChatInput";

describe("ChatInput", () => {
  it("does not render the removed sample question chips", () => {
    render(
      <ChatInput
        value=""
        onChange={vi.fn()}
        onSubmit={vi.fn()}
        onUpload={vi.fn()}
        onRemoveAttachment={vi.fn()}
        attachments={[]}
        isSubmitting={false}
        isUploading={false}
      />,
    );

    expect(screen.queryByText("Why is pipeline conversion dropping?")).not.toBeInTheDocument();
    expect(screen.queryByText("Generate SQL for this question")).not.toBeInTheDocument();
  });
});
