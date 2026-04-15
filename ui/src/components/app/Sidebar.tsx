import { Link } from "react-router-dom";
import { Button } from "@/components/shared/Button";
import { Drawer } from "@/components/shared/Drawer";
import { ThemeToggle } from "@/components/shared/ThemeToggle";
import { useAuth } from "@/hooks/useAuth";
import { sidebarNavItems } from "@/lib/constants";
import { classNames } from "@/lib/classNames";
import { formatRelativeTime } from "@/lib/utils";
import type { Conversation } from "@/types/chat";

type SidebarSection = "chats" | "uploads" | "saved" | "dashboards";

interface SidebarProps {
  conversations: Conversation[];
  activeSection: SidebarSection;
  activeConversationId: string;
  collapsed: boolean;
  isMobile: boolean;
  mobileOpen: boolean;
  onSelectSection: (section: SidebarSection) => void;
  onSelectConversation: (conversationId: string) => void;
  onNewChat: () => void;
  onToggleCollapse: () => void;
  onCloseMobile: () => void;
}

const navIcons = {
  chats: (
    <path d="M3 4.5C3 3.67 3.67 3 4.5 3H11.75C12.58 3 13.25 3.67 13.25 4.5V9C13.25 9.83 12.58 10.5 11.75 10.5H7L4 13V10.5H4.5C3.67 10.5 3 9.83 3 9V4.5Z" />
  ),
  uploads: (
    <path d="M8 11V3.5M8 3.5L5.5 6M8 3.5L10.5 6M3 12.5V13.25C3 14.22 3.78 15 4.75 15H11.25C12.22 15 13 14.22 13 13.25V12.5" />
  ),
  saved: (
    <path d="M4.5 3H11.5C12.33 3 13 3.67 13 4.5V13L8 10.5L3 13V4.5C3 3.67 3.67 3 4.5 3Z" />
  ),
  dashboards: <path d="M3 3.5H7V8H3V3.5ZM9 3.5H13V6H9V3.5ZM9 8H13V12.5H9V8ZM3 10H7V12.5H3V10Z" />,
};

function BrandMark({ showExpandCue = false }: { showExpandCue?: boolean }) {
  return (
    <div
      className={classNames(
        "relative flex h-11 w-11 items-center justify-center overflow-hidden rounded-2xl bg-contrast text-sm font-semibold text-contrast-foreground shadow-card transition-all duration-300",
        showExpandCue && "group-hover:shadow-soft",
      )}
    >
      <span className={classNames("relative z-[1] transition-opacity duration-300", showExpandCue && "group-hover:opacity-0")}>P</span>
      {showExpandCue ? (
        <>
          <span aria-hidden="true" className="pointer-events-none absolute inset-0 bg-contrast-foreground/10 opacity-0 transition-opacity duration-300 group-hover:opacity-100" />
          <svg
            aria-hidden="true"
            className="pointer-events-none absolute z-[2] h-4 w-4 -translate-x-1 text-contrast-foreground opacity-0 transition-all duration-300 group-hover:translate-x-0 group-hover:opacity-100"
            viewBox="0 0 16 16"
            fill="none"
          >
            <path d="M6 3.5L10 8L6 12.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </>
      ) : null}
    </div>
  );
}

function SidebarContent({
  conversations,
  activeSection,
  activeConversationId,
  collapsed,
  onSelectSection,
  onSelectConversation,
  onNewChat,
  onToggleCollapse,
  onAfterSelect,
}: Omit<SidebarProps, "isMobile" | "mobileOpen" | "onCloseMobile"> & { onAfterSelect?: () => void }) {
  const { user, logout } = useAuth();

  return (
    <div className={classNames("flex h-full w-full min-w-0 flex-col gap-5 overflow-hidden", collapsed ? "items-center px-4 py-4" : "p-4")}>
      <div className={classNames("flex min-w-0 items-center gap-2", collapsed ? "justify-center" : "justify-between")}>
        {collapsed ? (
          <button
            type="button"
            onClick={onToggleCollapse}
            className="group relative inline-flex h-11 w-11 items-center justify-center rounded-2xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/30 focus-visible:ring-offset-2 focus-visible:ring-offset-surface"
            aria-label="Expand sidebar"
          >
            <BrandMark showExpandCue />
          </button>
        ) : (
          <>
            <Link to="/" className="flex min-w-0 items-center gap-3">
              <BrandMark />
              <div className="min-w-0">
                <p className="truncate text-lg font-semibold text-ink">Planera</p>
                <p className="truncate text-xs tracking-[0.16em] text-muted uppercase">Analytics Copilot</p>
              </div>
            </Link>
            <button
              type="button"
              onClick={onToggleCollapse}
              className="hidden h-10 w-10 items-center justify-center rounded-full border border-line bg-panel text-muted transition-colors duration-300 hover:text-ink lg:inline-flex"
              aria-label="Collapse sidebar"
            >
              <svg className="h-4 w-4" viewBox="0 0 16 16" fill="none">
                <path d="M10 3.5L6 8L10 12.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </button>
          </>
        )}
      </div>

      <Button
        fullWidth={!collapsed}
        className={collapsed ? "!mx-auto !h-12 !w-12 !rounded-2xl !gap-0 !px-0" : ""}
        onClick={() => { onNewChat(); onAfterSelect?.(); }}
      >
        <svg
          className={classNames("shrink-0", collapsed ? "h-[18px] w-[18px]" : "h-4 w-4")}
          viewBox={collapsed ? "0 0 18 18" : "0 0 16 16"}
          fill="none"
        >
          <path
            d={collapsed ? "M9 3.5V14.5M3.5 9H14.5" : "M8 3V13M3 8H13"}
            stroke="currentColor"
            strokeWidth={collapsed ? 1.8 : 1.5}
            strokeLinecap="round"
          />
        </svg>
        {!collapsed ? "New Chat" : null}
      </Button>

      <ThemeToggle
        showLabel={!collapsed}
        className={classNames(collapsed ? "!mx-auto" : "w-full justify-start rounded-2xl px-3")}
      />

      <div className={classNames("space-y-2", collapsed && "w-full")}>
        {sidebarNavItems.map((item) => {
          const active = item.id === activeSection;
          return (
            <button
              key={item.id}
              type="button"
              onClick={() => {
                onSelectSection(item.id);
                onAfterSelect?.();
              }}
              className={classNames(
                collapsed
                  ? "mx-auto flex h-12 w-12 items-center justify-center rounded-2xl p-0 transition"
                  : "flex w-full items-center gap-3 rounded-2xl px-3 py-3 text-sm transition",
                active ? "bg-contrast text-contrast-foreground shadow-card" : "text-muted hover:bg-panel hover:text-ink",
              )}
            >
              <svg className="h-4 w-4 shrink-0" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round">
                {navIcons[item.id]}
              </svg>
              {!collapsed ? <span>{item.label}</span> : null}
            </button>
          );
        })}
      </div>

      {!collapsed ? (
        <div className="min-h-0 min-w-0 flex-1 overflow-hidden">
          <div className="flex h-full min-w-0 flex-col overflow-hidden rounded-[24px] border border-line bg-panel p-3">
            <div className="mb-2 flex items-center justify-between">
              <p className="text-xs font-medium uppercase tracking-[0.14em] text-muted">Recent chats</p>
              <span className="text-xs text-muted">{conversations.length}</span>
            </div>
            <div className="scroll-fade flex-1 space-y-2 overflow-y-auto pr-1">
              {conversations.map((conversation) => {
                const lastMessage = conversation.messages[conversation.messages.length - 1]?.content ?? "No messages yet";
                const active = conversation.id === activeConversationId;

                return (
                  <button
                    key={conversation.id}
                    type="button"
                    onClick={() => {
                      onSelectConversation(conversation.id);
                      onSelectSection("chats");
                      onAfterSelect?.();
                    }}
                    className={classNames(
                      "w-full rounded-2xl border px-3 py-3 text-left transition",
                      active ? "border-ink/10 bg-surface shadow-card" : "border-transparent hover:border-line hover:bg-surface",
                    )}
                  >
                    <p className="truncate text-sm font-semibold text-ink">{conversation.title}</p>
                    <p className="mt-1 truncate text-xs leading-5 text-muted">{lastMessage}</p>
                    <p className="mt-2 text-[11px] uppercase tracking-[0.14em] text-muted">{formatRelativeTime(conversation.updatedAt)}</p>
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      ) : (
        <div className="flex-1" />
      )}

      {!collapsed && user ? <p className="truncate px-1 text-xs text-muted">{user.email}</p> : null}

      <button
        type="button"
        onClick={logout}
        aria-label="Sign out"
        className={classNames(
          collapsed
            ? "mx-auto flex h-12 w-12 items-center justify-center rounded-2xl p-0 text-sm text-muted transition hover:bg-panel hover:text-ink"
            : "flex w-full items-center gap-3 rounded-2xl px-3 py-3 text-sm text-muted transition hover:bg-panel hover:text-ink",
        )}
      >
        <svg className="h-4 w-4 shrink-0" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round">
          <path d="M6.5 14H3.17A1.67 1.67 0 0 1 1.5 12.33V3.67A1.67 1.67 0 0 1 3.17 2H6.5M10.5 11.33 14 8 10.5 4.67M14 8H6" />
        </svg>
        {!collapsed ? "Sign out" : null}
      </button>

      <Link
        to="/settings"
        className={classNames(
          collapsed
            ? "mx-auto flex h-12 w-12 items-center justify-center rounded-2xl p-0 text-sm text-muted transition hover:bg-panel hover:text-ink"
            : "flex items-center gap-3 rounded-2xl px-3 py-3 text-sm text-muted transition hover:bg-panel hover:text-ink",
        )}
      >
        <svg className="h-4 w-4 shrink-0" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round">
          <path d="M8 3.5V2.5M8 13.5V12.5M11.18 4.82L11.88 4.12M4.12 11.88L4.82 11.18M12.5 8H13.5M2.5 8H3.5M11.18 11.18L11.88 11.88M4.12 4.12L4.82 4.82M10.5 8C10.5 9.38 9.38 10.5 8 10.5C6.62 10.5 5.5 9.38 5.5 8C5.5 6.62 6.62 5.5 8 5.5C9.38 5.5 10.5 6.62 10.5 8Z" />
        </svg>
        {!collapsed ? "Settings" : null}
      </Link>
    </div>
  );
}

export function Sidebar(props: SidebarProps) {
  const desktopWidth = props.collapsed ? "lg:w-[84px]" : "lg:w-[320px]";

  return (
    <>
      <aside
        className={classNames(
          "hidden shrink-0 overflow-hidden border-r border-line/80 bg-surface/95 lg:sticky lg:top-0 lg:flex lg:h-screen lg:self-start lg:transition-[width] lg:duration-300 lg:ease-in-out motion-reduce:transition-none",
          desktopWidth,
        )}
      >
        <SidebarContent {...props} onAfterSelect={undefined} />
      </aside>
      <Drawer open={props.mobileOpen} onClose={props.onCloseMobile} side="left" title="Planera" subtitle="Navigation">
        <SidebarContent {...props} collapsed={false} onAfterSelect={props.onCloseMobile} />
      </Drawer>
    </>
  );
}
