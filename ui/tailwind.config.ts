import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        canvas: "#f4efe8",
        surface: "#faf7f2",
        panel: "#fffdf9",
        elevated: "#f7f2ea",
        line: "#d9d0c4",
        ink: "#161819",
        muted: "#636c72",
        accent: {
          DEFAULT: "#235852",
          soft: "#d9ebe7",
          strong: "#193f3b",
        },
        sand: "#ece3d5",
        success: "#2f6d5a",
        warning: "#8a6227",
        danger: "#8c4141",
      },
      fontFamily: {
        sans: ['"Inter"', '"Avenir Next"', '"Segoe UI"', "system-ui", "sans-serif"],
        display: ['"Iowan Old Style"', '"Palatino Linotype"', "Georgia", "serif"],
        mono: ['"SFMono-Regular"', '"SF Mono"', "ui-monospace", "monospace"],
      },
      boxShadow: {
        soft: "0 16px 48px rgba(24, 32, 34, 0.07)",
        card: "0 12px 28px rgba(24, 32, 34, 0.06)",
        focus: "0 0 0 3px rgba(35, 88, 82, 0.16)",
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
