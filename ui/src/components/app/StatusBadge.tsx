import { classNames } from "@/lib/classNames";

interface StatusBadgeProps {
  label: string;
  tone?: "neutral" | "accent" | "success" | "warning" | "danger";
}

const toneStyles = {
  neutral: "border-line bg-surface text-muted",
  accent: "border-accent/15 bg-accent-soft text-accent-strong",
  success: "border-green-200 bg-green-50 text-success",
  warning: "border-amber-200 bg-amber-50 text-warning",
  danger: "border-red-200 bg-red-50 text-danger",
};

export function StatusBadge({ label, tone = "neutral" }: StatusBadgeProps) {
  return (
    <span className={classNames("inline-flex items-center rounded-full border px-3 py-1 text-xs font-medium", toneStyles[tone])}>
      {label}
    </span>
  );
}
