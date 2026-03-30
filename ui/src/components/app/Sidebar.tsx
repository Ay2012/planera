import { Link } from "react-router-dom";
import { Button } from "@/components/shared/Button";
import { Drawer } from "@/components/shared/Drawer";
import { UploadCard } from "@/components/app/UploadCard";
import { sidebarNavItems } from "@/lib/constants";
import { classNames } from "@/lib/classNames";
import { formatRelativeTime } from "@/lib/utils";
import type { Conversation } from "@/types/chat";
import type { UploadedAsset } from "@/types/upload";

type SidebarSection = "chats" | "uploads" | "saved" | "dashboards";

interface SidebarProps {
  conversations: Conversation[];
  uploads: UploadedAsset[];
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

function SidebarContent({
  conversations,
  uploads,
  activeSection,
  activeConversationId,
  collapsed,
  onSelectSection,
  onSelectConversation,
  onNewChat,
  onToggleCollapse,
  onAfterSelect,
}: Omit<SidebarProps, "isMobile" | "mobileOpen" | "onCloseMobile"> & { onAfterSelect?: () => void }) {
  return (
    <div className="flex h-full min-w-0 flex-col gap-5 overflow-hidden p-4">
      <div className="flex min-w-0 items-center justify-between gap-2">
        <Link to="/" className="flex min-w-0 items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-ink text-sm font-semibold text-white shadow-card">
            P
          </div>
          {!collapsed ? (
            <div className="min-w-0">
              <p className="truncate text-lg font-semibold text-ink">Planera</p>
              <p className="truncate text-xs tracking-[0.16em] text-muted uppercase">Analytics Copilot</p>
            </div>
          ) : null}
        </Link>
        <button
          type="button"
          onClick={onToggleCollapse}
          className="hidden h-10 w-10 items-center justify-center rounded-full border border-line bg-panel text-muted transition hover:text-ink lg:inline-flex"
          aria-label="Collapse sidebar"
        >
          <svg className="h-4 w-4" viewBox="0 0 16 16" fill="none">
            <path d="M6 3.5L10 8L6 12.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>
      </div>

      <Button fullWidth={!collapsed} className={collapsed ? "h-12 w-12 rounded-2xl px-0" : ""} onClick={() => { onNewChat(); onAfterSelect?.(); }}>
        <svg className="h-4 w-4" viewBox="0 0 16 16" fill="none">
          <path d="M8 3V13M3 8H13" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
        </svg>
        {!collapsed ? "New Chat" : null}
      </Button>

      <div className="space-y-2">
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
                "flex w-full items-center gap-3 rounded-2xl px-3 py-3 text-sm transition",
                active ? "bg-ink text-white shadow-card" : "text-muted hover:bg-panel hover:text-ink",
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

      {!collapsed ? (
        <div className="min-w-0 shrink-0 space-y-3">
          <div className="flex items-center justify-between">
            <p className="text-xs font-medium uppercase tracking-[0.14em] text-muted">Recent uploads</p>
            <button
              type="button"
              onClick={() => {
                onSelectSection("uploads");
                onAfterSelect?.();
              }}
              className="text-xs text-accent"
            >
              View all
            </button>
          </div>
          <div className="space-y-3">
            {uploads.slice(0, 2).map((asset) => (
              <UploadCard key={asset.id} asset={asset} />
            ))}
          </div>
        </div>
      ) : null}

      <Link
        to="/settings"
        className={classNames(
          "flex items-center gap-3 rounded-2xl px-3 py-3 text-sm text-muted transition hover:bg-panel hover:text-ink",
          collapsed && "justify-center",
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
  const desktopWidth = props.collapsed ? "lg:w-[92px]" : "lg:w-[320px]";

  return (
    <>
      <aside
        className={classNames(
          "hidden h-screen shrink-0 overflow-hidden border-r border-line/80 bg-surface/95 lg:flex",
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
