import type { TextareaHTMLAttributes } from "react";
import { classNames } from "@/lib/classNames";

export function Textarea({ className, ...props }: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      className={classNames(
        "min-h-[120px] w-full rounded-[24px] border border-line bg-panel px-4 py-3 text-sm text-ink placeholder:text-muted shadow-[inset_0_1px_0_rgba(255,255,255,0.6)] transition focus:border-accent/40",
        className,
      )}
      {...props}
    />
  );
}
