import type { HTMLAttributes, PropsWithChildren } from "react";
import { classNames } from "@/lib/classNames";

interface CardProps extends HTMLAttributes<HTMLDivElement>, PropsWithChildren {
  elevated?: boolean;
}

export function Card({ children, className, elevated = false, ...props }: CardProps) {
  return (
    <div
      className={classNames(
        "rounded-[22px] border border-line/90 bg-panel surface-ring",
        elevated ? "shadow-soft" : "shadow-card",
        className,
      )}
      {...props}
    >
      {children}
    </div>
  );
}
