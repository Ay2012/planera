import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        canvas: "rgb(var(--color-canvas) / <alpha-value>)",
        surface: "rgb(var(--color-surface) / <alpha-value>)",
        panel: "rgb(var(--color-panel) / <alpha-value>)",
        elevated: "rgb(var(--color-elevated) / <alpha-value>)",
        line: "rgb(var(--color-line) / <alpha-value>)",
        ink: "rgb(var(--color-ink) / <alpha-value>)",
        muted: "rgb(var(--color-muted) / <alpha-value>)",
        contrast: {
          DEFAULT: "rgb(var(--color-contrast) / <alpha-value>)",
          foreground: "rgb(var(--color-contrast-foreground) / <alpha-value>)",
        },
        accent: {
          DEFAULT: "rgb(var(--color-accent) / <alpha-value>)",
          soft: "rgb(var(--color-accent-soft) / <alpha-value>)",
          strong: "rgb(var(--color-accent-strong) / <alpha-value>)",
        },
        success: {
          DEFAULT: "rgb(var(--color-success) / <alpha-value>)",
          soft: "rgb(var(--color-success-soft) / <alpha-value>)",
        },
        warning: {
          DEFAULT: "rgb(var(--color-warning) / <alpha-value>)",
          soft: "rgb(var(--color-warning-soft) / <alpha-value>)",
        },
        danger: {
          DEFAULT: "rgb(var(--color-danger) / <alpha-value>)",
          soft: "rgb(var(--color-danger-soft) / <alpha-value>)",
        },
        code: {
          DEFAULT: "rgb(var(--color-code) / <alpha-value>)",
          ink: "rgb(var(--color-code-ink) / <alpha-value>)",
        },
      },
      fontFamily: {
        sans: ['"Inter"', '"Avenir Next"', '"Segoe UI"', "system-ui", "sans-serif"],
        display: ['"Iowan Old Style"', '"Palatino Linotype"', "Georgia", "serif"],
        mono: ['"SFMono-Regular"', '"SF Mono"', "ui-monospace", "monospace"],
      },
      boxShadow: {
        soft: "var(--shadow-soft)",
        card: "var(--shadow-card)",
        field: "var(--shadow-field)",
        focus: "0 0 0 3px rgb(var(--color-accent) / 0.16)",
      },
      borderRadius: {
        xl2: "1.4rem",
      },
      backgroundImage: {
        "hero-glow":
          "radial-gradient(circle at top left, rgba(35, 88, 82, 0.08), transparent 38%), radial-gradient(circle at right, rgba(193, 171, 133, 0.08), transparent 32%)",
      },
    },
  },
  plugins: [],
};

export default config;
