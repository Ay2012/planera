import { Card } from "@/components/shared/Card";
import type { ResultTableData } from "@/types/inspection";

interface ResultTableProps {
  title?: string;
  table: ResultTableData;
}

export function ResultTable({ title, table }: ResultTableProps) {
  return (
    <Card className="max-w-full min-w-0 overflow-hidden">
      {title ? <div className="border-b border-line px-4 py-3 text-sm font-semibold text-ink">{title}</div> : null}
      <div className="scroll-fade max-w-full overflow-x-auto">
        <table className="min-w-full divide-y divide-line text-sm">
          <thead className="bg-surface">
            <tr>
              {table.columns.map((column) => (
                <th key={column} className="px-4 py-3 text-left font-medium text-muted">
                  {column}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-line/70 bg-panel">
            {table.rows.map((row, rowIndex) => (
              <tr key={rowIndex}>
                {table.columns.map((column) => (
                  <td key={column} className="whitespace-nowrap px-4 py-3 text-ink">
                    {row[column] ?? "—"}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
