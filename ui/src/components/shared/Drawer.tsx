import { useEffect, type ReactNode } from "react";
import { classNames } from "@/lib/classNames";

interface DrawerProps {
  open: boolean;
  onClose: () => void;
  title?: string;
  subtitle?: string;
  side?: "left" | "right";
  maximized?: boolean;
  actions?: ReactNode;
  children: ReactNode;
}

export function Drawer({
  open,
  onClose,
  title,
  subtitle,
  side = "right",
  maximized = false,
  actions,
  children,
}: DrawerProps) {
  useEffect(() => {
    if (!open) return;

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    };

    document.body.classList.add("drawer-open");
    window.addEventListener("keydown", onKeyDown);

    return () => {
      document.body.classList.remove("drawer-open");
      window.removeEventListener("keydown", onKeyDown);
    };
  }, [open, onClose]);

  return (
    <div
      className={classNames(
        "pointer-events-none fixed inset-0 z-50 transition duration-200",
        open ? "visible" : "invisible",
      )}
      aria-hidden={!open}
    >
      <div
        className={classNames(
          "pointer-events-auto absolute inset-0 bg-black/18 backdrop-blur-[2px] transition duration-200",
          open ? "opacity-100" : "opacity-0",
        )}
        onClick={onClose}
      />
      <div
        className={classNames(
          "pointer-events-auto absolute top-0 h-full border-line/90 bg-panel shadow-soft transition duration-300",
          side === "right"
            ? "right-0 border-l"
            : "left-0 border-r",
          maximized
            ? "w-full lg:w-[min(88vw,980px)]"
            : "w-full sm:w-[min(92vw,560px)] lg:w-[520px]",
          open
            ? "translate-x-0"
            : side === "right"
              ? "translate-x-full"
              : "-translate-x-full",
        )}
      >
        <div className="flex h-full flex-col">
          <div className="border-b border-line/80 px-5 py-4">
            <div className="flex items-start justify-between gap-4">
              <div>
                {title ? <h2 className="text-lg font-semibold text-ink">{title}</h2> : null}
                {subtitle ? <p className="mt-1 text-sm text-muted">{subtitle}</p> : null}
              </div>
              <div className="flex items-center gap-2">
                {actions}
                <button
                  type="button"
                  onClick={onClose}
                  className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-line bg-surface text-muted transition hover:text-ink"
                  aria-label="Close panel"
                >
                  <svg className="h-4 w-4" viewBox="0 0 16 16" fill="none">
                    <path d="M4 4L12 12M12 4L4 12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                  </svg>
                </button>
              </div>
            </div>
          </div>
          <div className="scroll-fade flex-1 overflow-y-auto">{children}</div>
        </div>
      </div>
    </div>
  );
}
