import { classNames } from "@/lib/classNames";

interface StatusBadgeProps {
  label: string;
  tone?: "neutral" | "accent" | "success" | "warning" | "danger";
}

const toneStyles = {
  neutral: "border-line bg-surface text-muted",
  accent: "border-accent/15 bg-accent-soft text-accent-strong",
  success: "border-success/20 bg-success-soft text-success",
  warning: "border-warning/20 bg-warning-soft text-warning",
  danger: "border-danger/20 bg-danger-soft text-danger",
};

export function StatusBadge({ label, tone = "neutral" }: StatusBadgeProps) {
  return (
    <span className={classNames("inline-flex items-center rounded-full border px-3 py-1 text-xs font-medium", toneStyles[tone])}>
      {label}
    </span>
  );
}
