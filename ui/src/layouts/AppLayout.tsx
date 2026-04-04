import type { PropsWithChildren, ReactNode } from "react";
import { classNames } from "@/lib/classNames";

interface AppLayoutProps extends PropsWithChildren {
  sidebar: ReactNode;
  header: ReactNode;
  footer?: ReactNode;
  inspectionPanel?: ReactNode;
  contentClassName?: string;
}

export function AppLayout({ sidebar, header, footer, inspectionPanel, contentClassName, children }: AppLayoutProps) {
  return (
    <div className="min-h-screen overflow-x-hidden bg-canvas lg:h-screen lg:overflow-hidden">
      <div className="min-h-screen lg:grid lg:h-full lg:grid-cols-[auto_minmax(0,1fr)]">
        {sidebar}
        <div className="flex min-w-0 flex-col overflow-x-hidden lg:h-screen lg:min-h-0">
          {header}
          <main className={classNames("min-w-0 flex-1 overflow-x-hidden lg:min-h-0 lg:overflow-y-auto", contentClassName)}>
            {children}
          </main>
          {footer}
        </div>
      </div>
      {inspectionPanel}
    </div>
  );
}
