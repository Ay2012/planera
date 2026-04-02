import { useEffect, useState } from "react";
import { uiStore } from "@/store/uiStore";

const MOBILE_BREAKPOINT = 1024;

export function useResponsiveSidebar() {
  const [isMobile, setIsMobile] = useState(() => window.innerWidth < MOBILE_BREAKPOINT);
  const [collapsed, setCollapsed] = useState(() => uiStore.getSidebarCollapsed());
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    const onResize = () => {
      const nextMobile = window.innerWidth < MOBILE_BREAKPOINT;
      setIsMobile(nextMobile);
      if (!nextMobile) {
        setMobileOpen(false);
      }
    };

    onResize();
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

  const toggleSidebar = () => {
    if (isMobile) {
      setMobileOpen((value) => !value);
      return;
    }

    setCollapsed((value) => {
      const next = !value;
      uiStore.setSidebarCollapsed(next);
      return next;
    });
  };

  return {
    isMobile,
    collapsed,
    mobileOpen,
    openMobileSidebar: () => setMobileOpen(true),
    closeMobileSidebar: () => setMobileOpen(false),
    toggleSidebar,
  };
}
