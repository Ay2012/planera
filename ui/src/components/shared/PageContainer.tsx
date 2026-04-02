import type { PropsWithChildren } from "react";
import { classNames } from "@/lib/classNames";

interface PageContainerProps extends PropsWithChildren {
  className?: string;
}

export function PageContainer({ children, className }: PageContainerProps) {
  return <div className={classNames("mx-auto w-full min-w-0 max-w-[1240px] px-5 sm:px-8", className)}>{children}</div>;
}
