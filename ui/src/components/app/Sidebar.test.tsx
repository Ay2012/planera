import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { Sidebar } from "@/components/app/Sidebar";
import { AuthContext } from "@/context/auth-context";

describe("Sidebar", () => {
  it("does not render a recent uploads section", () => {
    render(
      <MemoryRouter>
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
          />
        </AuthContext.Provider>
      </MemoryRouter>,
    );

    expect(screen.queryByText("Recent uploads")).not.toBeInTheDocument();
  });
});
