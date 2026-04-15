const keys = {
  sidebarCollapsed: "planera.sidebar.collapsed",
  activeSection: "planera.active.section",
  activeConversation: "planera.active.conversation",
  theme: "planera.theme",
};

type ThemePreference = "light" | "dark";

export const uiStore = {
  getSidebarCollapsed() {
    return window.localStorage.getItem(keys.sidebarCollapsed) === "true";
  },
  setSidebarCollapsed(value: boolean) {
    window.localStorage.setItem(keys.sidebarCollapsed, String(value));
  },
  getActiveSection() {
    return window.localStorage.getItem(keys.activeSection) ?? "chats";
  },
  setActiveSection(value: string) {
    window.localStorage.setItem(keys.activeSection, value);
  },
  getActiveConversation() {
    return window.localStorage.getItem(keys.activeConversation) ?? "";
  },
  setActiveConversation(value: string) {
    window.localStorage.setItem(keys.activeConversation, value);
  },
  getTheme(): ThemePreference | null {
    const value = window.localStorage.getItem(keys.theme);
    return value === "light" || value === "dark" ? value : null;
  },
  setTheme(value: ThemePreference) {
    window.localStorage.setItem(keys.theme, value);
  },
};
