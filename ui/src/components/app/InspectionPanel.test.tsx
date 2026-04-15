import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { InspectionPanel } from "@/components/app/InspectionPanel";
import type { InspectionData } from "@/types/inspection";

const inspection: InspectionData = {
  id: "inspection_1",
  title: "Enterprise conversion review",
  status: "valid",
  verified: true,
  queryType: "SQL",
  engine: "DuckDB",
  dataSource: "Revenue warehouse",
  rowsReturned: 3,
  lastUpdated: "2026-04-14T12:00:00.000Z",
  filters: ["segment = enterprise"],
  query: "select * from revenue_pipeline",
  runtimeMs: 814,
  confidence: 0.92,
  metadata: [
    { label: "Warehouse", value: "Revenue warehouse" },
    { label: "Model", value: "revenue_pipeline" },
  ],
  results: {
    columns: ["segment", "conversion_rate"],
    rows: [{ segment: "Enterprise", conversion_rate: "34.1%" }],
  },
  trace: [
    {
      id: "trace_1",
      label: "Compiled SQL",
      description: "The query writer produced the final SQL for execution.",
      detail: "1 statement compiled.",
      durationLabel: "142 ms",
      status: "complete",
    },
  ],
  validation: [
    {
      id: "validation_1",
      label: "Query valid",
      detail: "SQL parsed and executed without syntax errors.",
      status: "pass",
    },
  ],
};

describe("InspectionPanel", () => {
  it("renders without an expand control and uses the wide drawer layout", () => {
    render(
      <InspectionPanel
        open
        loading={false}
        error={null}
        inspection={inspection}
        activeTab="sql"
        onClose={vi.fn()}
        onTabChange={vi.fn()}
      />,
    );

    expect(screen.queryByRole("button", { name: /expand|collapse/i })).not.toBeInTheDocument();

    const dialog = screen.getByRole("dialog", { name: "Enterprise conversion review" });
    expect(dialog.className).toContain("lg:w-[min(88vw,980px)]");
  });
});
