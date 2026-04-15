import { forwardRef, type TextareaHTMLAttributes } from "react";
import { classNames } from "@/lib/classNames";

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaHTMLAttributes<HTMLTextAreaElement>>(function Textarea(
  { className, ...props },
  ref,
) {
  return (
    <textarea
      ref={ref}
      className={classNames(
        "w-full rounded-[24px] border border-line bg-panel px-4 py-3 text-sm leading-5 text-ink placeholder:text-muted shadow-field transition focus:border-accent/40",
        className,
      )}
      {...props}
    />
  );
});
