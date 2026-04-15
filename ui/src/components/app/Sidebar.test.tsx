import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { Sidebar } from "@/components/app/Sidebar";
import { ThemeProvider } from "@/context/ThemeProvider";
import { AuthContext } from "@/context/auth-context";

describe("Sidebar", () => {
  const renderSidebar = (props?: Partial<React.ComponentProps<typeof Sidebar>>) =>
    render(
      <MemoryRouter>
        <ThemeProvider>
          <AuthContext.Provider
            value={{
              user: {
                id: 1,
                email: "test@example.com",
                display_name: null,
                created_at: new Date().toISOString(),
              },
              token: "token_123",
              isReady: true,
              isAuthenticated: true,
              login: vi.fn(),
              signUp: vi.fn(),
              logout: vi.fn(),
            }}
          >
            <Sidebar
              conversations={[]}
              activeSection="chats"
              activeConversationId=""
              collapsed={false}
              isMobile={false}
              mobileOpen={false}
              onSelectSection={vi.fn()}
              onSelectConversation={vi.fn()}
              onNewChat={vi.fn()}
              onToggleCollapse={vi.fn()}
              onCloseMobile={vi.fn()}
              {...props}
            />
          </AuthContext.Provider>
        </ThemeProvider>
      </MemoryRouter>,
    );

  it("does not render a recent uploads section", () => {
    renderSidebar();

    expect(screen.queryByText("Recent uploads")).not.toBeInTheDocument();
  });

  it("renders the theme toggle in collapsed and mobile sidebar states", () => {
    const { rerender } = renderSidebar({ collapsed: true });

    expect(screen.getAllByRole("button", { name: "Switch to dark mode" }).length).toBeGreaterThan(0);

    rerender(
      <MemoryRouter>
        <ThemeProvider>
          <AuthContext.Provider
            value={{
              user: {
                id: 1,
                email: "test@example.com",
                display_name: null,
                created_at: new Date().toISOString(),
              },
              token: "token_123",
              isReady: true,
              isAuthenticated: true,
              login: vi.fn(),
              signUp: vi.fn(),
              logout: vi.fn(),
            }}
          >
            <Sidebar
              conversations={[]}
              activeSection="chats"
              activeConversationId=""
              collapsed={false}
              isMobile
              mobileOpen
              onSelectSection={vi.fn()}
              onSelectConversation={vi.fn()}
              onNewChat={vi.fn()}
              onToggleCollapse={vi.fn()}
              onCloseMobile={vi.fn()}
            />
          </AuthContext.Provider>
        </ThemeProvider>
      </MemoryRouter>,
    );

    expect(screen.getAllByRole("button", { name: "Switch to dark mode" }).length).toBeGreaterThan(0);
  });
});
