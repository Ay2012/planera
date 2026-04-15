import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { Navbar } from "@/components/marketing/Navbar";
import { ThemeProvider } from "@/context/ThemeProvider";

describe("Navbar", () => {
  it("renders the theme toggle in the marketing navigation", () => {
    render(
      <MemoryRouter>
        <ThemeProvider>
          <Navbar />
        </ThemeProvider>
      </MemoryRouter>,
    );

    expect(screen.getAllByRole("button", { name: "Switch to dark mode" })).toHaveLength(2);
  });
});
