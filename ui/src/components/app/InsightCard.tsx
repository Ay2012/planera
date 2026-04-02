import { Card } from "@/components/shared/Card";
import { classNames } from "@/lib/classNames";

interface InsightCardProps {
  title: string;
  body: string;
  tone?: "neutral" | "positive" | "caution";
}

const toneStyles = {
  neutral: "bg-panel",
  positive: "bg-green-50/70",
  caution: "bg-amber-50/80",
};

export function InsightCard({ title, body, tone = "neutral" }: InsightCardProps) {
  return (
    <Card className={classNames("p-4", toneStyles[tone])}>
      <p className="text-sm font-semibold text-ink">{title}</p>
      <p className="mt-2 text-sm leading-6 text-muted">{body}</p>
    </Card>
  );
}
