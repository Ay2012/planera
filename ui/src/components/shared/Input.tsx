import type { InputHTMLAttributes } from "react";
import { classNames } from "@/lib/classNames";

export function Input({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={classNames(
        "h-11 w-full rounded-2xl border border-line bg-panel px-4 text-sm text-ink placeholder:text-muted shadow-field transition focus:border-accent/40",
        className,
      )}
      {...props}
    />
  );
}
