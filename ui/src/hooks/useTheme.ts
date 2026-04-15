import { useContext } from "react";
import { ThemeContext } from "@/context/theme-context";

export function useTheme() {
  const value = useContext(ThemeContext);

  if (!value) {
    throw new Error("useTheme must be used within a ThemeProvider.");
  }

  return value;
}
