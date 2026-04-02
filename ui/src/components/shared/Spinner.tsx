import { classNames } from "@/lib/classNames";

interface SpinnerProps {
  className?: string;
}

export function Spinner({ className }: SpinnerProps) {
  return (
    <span
      className={classNames(
        "inline-block h-5 w-5 animate-spin rounded-full border-2 border-line border-t-accent",
        className,
      )}
      aria-hidden="true"
    />
  );
}
