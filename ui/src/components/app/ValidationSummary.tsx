import { StatusBadge } from "@/components/app/StatusBadge";
import { Card } from "@/components/shared/Card";
import type { ValidationCheck } from "@/types/inspection";

interface ValidationSummaryProps {
  items: ValidationCheck[];
}

export function ValidationSummary({ items }: ValidationSummaryProps) {
  return (
    <div className="space-y-3">
      {items.map((item) => (
        <Card key={item.id} className="p-4">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-sm font-semibold text-ink">{item.label}</p>
              <p className="mt-2 text-sm leading-6 text-muted">{item.detail}</p>
            </div>
            <StatusBadge
              label={item.status === "pass" ? "Pass" : item.status === "warn" ? "Review" : "Fail"}
              tone={item.status === "pass" ? "success" : item.status === "warn" ? "warning" : "danger"}
            />
          </div>
        </Card>
      ))}
    </div>
  );
}
