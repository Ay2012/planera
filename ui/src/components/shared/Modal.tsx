import { useEffect, type ReactNode } from "react";
import { classNames } from "@/lib/classNames";

interface ModalProps {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
}

export function Modal({ open, onClose, title, children }: ModalProps) {
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
    >
      <button
        type="button"
        onClick={onClose}
        className={classNames(
          "pointer-events-auto absolute inset-0 bg-black/18 backdrop-blur-[2px] transition duration-200",
          open ? "opacity-100" : "opacity-0",
        )}
        aria-label="Close modal backdrop"
      />
      <div className="pointer-events-none flex min-h-full items-center justify-center p-4">
        <div
          className={classNames(
            "pointer-events-auto w-full max-w-3xl rounded-[28px] border border-line bg-panel shadow-soft transition duration-300",
            open ? "translate-y-0 opacity-100" : "translate-y-6 opacity-0",
          )}
          role="dialog"
          aria-modal="true"
          aria-label={title}
        >
          <div className="flex items-center justify-between border-b border-line/80 px-6 py-4">
            <h2 className="text-lg font-semibold text-ink">{title}</h2>
            <button
              type="button"
              onClick={onClose}
              className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-line bg-surface text-muted transition hover:text-ink"
            >
              <svg className="h-4 w-4" viewBox="0 0 16 16" fill="none">
                <path d="M4 4L12 12M12 4L4 12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
              </svg>
            </button>
          </div>
          <div className="p-6">{children}</div>
        </div>
      </div>
    </div>
  );
}
