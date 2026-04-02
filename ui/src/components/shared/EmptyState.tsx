import type { ReactNode } from "react";
import { Button } from "@/components/shared/Button";
import { Card } from "@/components/shared/Card";

interface EmptyStateProps {
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
  icon?: ReactNode;
}

export function EmptyState({ title, description, actionLabel, onAction, icon }: EmptyStateProps) {
  return (
    <Card className="p-8 text-center">
      <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-accent-soft text-accent-strong">
        {icon ?? (
          <svg className="h-6 w-6" viewBox="0 0 24 24" fill="none">
            <path d="M4 6.5H20M4 12H20M4 17.5H14" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
        )}
      </div>
      <h3 className="text-xl font-semibold text-ink">{title}</h3>
      <p className="mx-auto mt-3 max-w-md text-sm leading-6 text-muted">{description}</p>
      {actionLabel && onAction ? (
        <div className="mt-5">
          <Button onClick={onAction}>{actionLabel}</Button>
        </div>
      ) : null}
    </Card>
  );
}
