import { classNames } from "@/lib/classNames";
import { useTheme } from "@/hooks/useTheme";

interface ThemeToggleProps {
  className?: string;
  showLabel?: boolean;
}

function SunIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="none" aria-hidden="true">
      <circle cx="10" cy="10" r="3.5" stroke="currentColor" strokeWidth="1.5" />
      <path d="M10 2.75V4.25M10 15.75V17.25M4.87 4.87L5.93 5.93M14.07 14.07L15.13 15.13M2.75 10H4.25M15.75 10H17.25M4.87 15.13L5.93 14.07M14.07 5.93L15.13 4.87" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

function MoonIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="none" aria-hidden="true">
      <path
        d="M15.1 11.72A6.35 6.35 0 0 1 8.28 4.9 6.7 6.7 0 1 0 15.1 11.72Z"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function ThemeToggle({ className, showLabel = false }: ThemeToggleProps) {
  const { theme, toggleTheme } = useTheme();
  const isDark = theme === "dark";
  const nextThemeLabel = isDark ? "light" : "dark";

  return (
    <button
      type="button"
      onClick={toggleTheme}
      className={classNames(
        "group inline-flex items-center gap-3 rounded-full border border-line bg-panel/92 px-3 py-2 text-sm text-muted shadow-card transition duration-300 hover:border-accent/20 hover:bg-surface hover:text-ink",
        showLabel ? "justify-start" : "h-11 w-11 justify-center px-0",
        className,
      )}
      aria-label={`Switch to ${nextThemeLabel} mode`}
      title={`Switch to ${nextThemeLabel} mode`}
    >
      <span className="relative flex h-9 w-9 items-center justify-center overflow-hidden rounded-full bg-accent-soft text-accent-strong">
        <SunIcon
          className={classNames(
            "absolute h-[18px] w-[18px] transition-all duration-500 ease-out",
            isDark ? "-rotate-90 scale-0 opacity-0" : "rotate-0 scale-100 opacity-100",
          )}
        />
        <MoonIcon
          className={classNames(
            "absolute h-[18px] w-[18px] transition-all duration-500 ease-out",
            isDark ? "rotate-0 scale-100 opacity-100" : "rotate-90 scale-0 opacity-0",
          )}
        />
      </span>
      {showLabel ? (
        <span className="flex min-w-0 flex-col items-start text-left leading-none">
          <span className="text-[11px] uppercase tracking-[0.16em] text-muted/80">Theme</span>
          <span className="mt-1 text-sm font-medium text-ink">{isDark ? "Dark mode" : "Light mode"}</span>
        </span>
      ) : null}
    </button>
  );
}
