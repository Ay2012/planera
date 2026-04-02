import { useCallback, useState } from "react";
import { fetchInspection } from "@/api/inspections";
import type { InspectionData, InspectionTabId } from "@/types/inspection";

export function useInspectionPanel() {
  const [open, setOpen] = useState(false);
  const [maximized, setMaximized] = useState(false);
  const [activeTab, setActiveTab] = useState<InspectionTabId>("sql");
  const [inspection, setInspection] = useState<InspectionData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const openInspection = useCallback(async (inspectionId: string, preferredTab: InspectionTabId = "sql") => {
    setOpen(true);
    setActiveTab(preferredTab);
    setLoading(true);
    setError(null);

    try {
      const response = await fetchInspection(inspectionId);
      setInspection(response.inspection);
    } catch (err) {
      setInspection(null);
      setError(err instanceof Error ? err.message : "Unable to load inspection details.");
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    open,
    maximized,
    activeTab,
    inspection,
    loading,
    error,
    setActiveTab,
    openInspection,
    closeInspection: () => setOpen(false),
    toggleMaximized: () => setMaximized((value) => !value),
  };
}
