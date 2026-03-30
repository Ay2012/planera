import { Button } from "@/components/shared/Button";
import { Card } from "@/components/shared/Card";

interface ErrorStateProps {
  title: string;
  description: string;
  onRetry?: () => void;
}

export function ErrorState({ title, description, onRetry }: ErrorStateProps) {
  return (
    <Card className="border-danger/20 bg-red-50/60 p-6">
      <div className="flex items-start gap-4">
        <div className="mt-1 rounded-full bg-red-100 p-2 text-danger">
          <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none">
            <path d="M12 8V13M12 17H12.01M10.29 3.86L1.82 18C1.64 18.31 1.55 18.47 1.54 18.6C1.51 18.96 1.7 19.31 2.02 19.49C2.13 19.55 2.33 19.55 2.74 19.55H21.26C21.67 19.55 21.87 19.55 21.98 19.49C22.3 19.31 22.49 18.96 22.46 18.6C22.45 18.47 22.36 18.31 22.18 18L13.71 3.86C13.5 3.51 13.39 3.34 13.25 3.22C12.8 2.82 12.2 2.82 11.75 3.22C11.61 3.34 11.5 3.51 11.29 3.86Z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
        <div className="flex-1">
          <h3 className="text-base font-semibold text-ink">{title}</h3>
          <p className="mt-2 text-sm leading-6 text-muted">{description}</p>
          {onRetry ? (
            <div className="mt-4">
              <Button variant="secondary" onClick={onRetry}>
                Retry
              </Button>
            </div>
          ) : null}
        </div>
      </div>
    </Card>
  );
}
