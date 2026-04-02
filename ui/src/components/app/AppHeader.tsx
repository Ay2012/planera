import { StatusBadge } from "@/components/app/StatusBadge";
import { classNames } from "@/lib/classNames";

interface AppHeaderProps {
  title: string;
  subtitle: string;
  uploadedLabel?: string;
  connectionLabel: string;
  connectionTone?: "neutral" | "accent" | "success" | "warning" | "danger";
  modeLabel?: string;
  modeTone?: "neutral" | "accent" | "success" | "warning" | "danger";
  onToggleSidebar: () => void;
  showMenuButton?: boolean;
}

export function AppHeader({
  title,
  subtitle,
  uploadedLabel,
  connectionLabel,
  connectionTone = "neutral",
  modeLabel,
  modeTone = "neutral",
  onToggleSidebar,
  showMenuButton = false,
}: AppHeaderProps) {
  return (
    <div className="sticky top-0 z-20 border-b border-line/80 bg-canvas/90 px-4 py-4 backdrop-blur sm:px-6">
      <div className="mx-auto flex w-full max-w-6xl min-w-0 flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
        <div className="flex min-w-0 items-start gap-3">
          <button
            type="button"
            onClick={onToggleSidebar}
            className={classNames(
              "mt-0.5 inline-flex h-10 w-10 items-center justify-center rounded-full border border-line bg-panel text-muted transition hover:text-ink lg:hidden",
              showMenuButton ? "" : "hidden",
            )}
            aria-label="Toggle sidebar"
          >
            <svg className="h-4 w-4" viewBox="0 0 16 16" fill="none">
              <path d="M3 4H13M3 8H13M3 12H13" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
          </button>
          <div className="min-w-0">
            <p className="text-xs font-medium uppercase tracking-[0.16em] text-muted">Planera Workspace</p>
            <h1 className="mt-1 text-2xl font-semibold text-ink">{title}</h1>
            <p className="mt-2 text-sm leading-6 text-muted">{subtitle}</p>
          </div>
        </div>
        <div className="flex max-w-full shrink-0 flex-wrap gap-2 xl:max-w-[320px] xl:justify-end">
          <StatusBadge label={connectionLabel} tone={connectionTone} />
          {uploadedLabel ? <StatusBadge label={uploadedLabel} tone="success" /> : null}
          {modeLabel ? <StatusBadge label={modeLabel} tone={modeTone} /> : null}
        </div>
      </div>
    </div>
  );
}
