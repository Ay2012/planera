import moonIcon from "@/assets/icons/moon.png";
import sunIcon from "@/assets/icons/sun.png";
import { MaskedIcon } from "@/components/shared/MaskedIcon";
import { classNames } from "@/lib/classNames";
import { useTheme } from "@/hooks/useTheme";

interface ThemeToggleProps {
  className?: string;
  showLabel?: boolean;
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
        "group inline-flex items-center rounded-full border border-line text-sm shadow-card transition duration-300 hover:border-accent/20 hover:text-ink",
        showLabel
          ? "gap-3 bg-panel/92 px-3 py-2 justify-start hover:bg-surface text-muted"
          : "h-11 w-11 justify-center bg-panel/88 p-0 text-accent-strong hover:bg-panel",
        className,
      )}
      aria-label={`Switch to ${nextThemeLabel} mode`}
      title={`Switch to ${nextThemeLabel} mode`}
    >
      <span
        className={classNames(
          "relative flex items-center justify-center overflow-hidden",
          showLabel
            ? "h-9 w-9 rounded-full bg-accent-soft text-accent-strong"
            : "h-8 w-8 rounded-full bg-transparent text-current",
        )}
      >
        <MaskedIcon
          src={sunIcon}
          className={classNames(
            "absolute h-[18px] w-[18px] transition-all duration-500 ease-out",
            isDark ? "-rotate-90 scale-0 opacity-0" : "rotate-0 scale-100 opacity-100",
          )}
        />
        <MaskedIcon
          src={moonIcon}
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
