import { useMemo, useState } from "react";
import { AppHeader } from "@/components/app/AppHeader";
import { ChatInput } from "@/components/app/ChatInput";
import { ChatThread } from "@/components/app/ChatThread";
import { InspectionPanel } from "@/components/app/InspectionPanel";
import { InsightCard } from "@/components/app/InsightCard";
import { Sidebar } from "@/components/app/Sidebar";
import { UploadsPanel } from "@/components/app/UploadsPanel";
import { StatusBadge } from "@/components/app/StatusBadge";
import { Button } from "@/components/shared/Button";
import { Card } from "@/components/shared/Card";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorState } from "@/components/shared/ErrorState";
import { PageContainer } from "@/components/shared/PageContainer";
import { Spinner } from "@/components/shared/Spinner";
import { savedAnalyses } from "@/data/mockInsights";
import { env, isDemoOnlyMode } from "@/config/env";
import { useChat } from "@/hooks/useChat";
import { useActiveUploads } from "@/hooks/useActiveUploads";
import { useInspectionPanel } from "@/hooks/useInspectionPanel";
import { useResponsiveSidebar } from "@/hooks/useResponsiveSidebar";
import { useUpload } from "@/hooks/useUpload";
import { AppLayout } from "@/layouts/AppLayout";
import { formatCompactNumber } from "@/lib/utils";
import { uiStore } from "@/store/uiStore";

type SidebarSection = "chats" | "uploads" | "saved" | "dashboards";

const dashboardMetrics = [
  { label: "Connected sources", value: "4", detail: "warehouse, postgres, csv, tsv" },
  { label: "Verified runs", value: "28", detail: "last 7 days" },
  { label: "Median runtime", value: "0.9s", detail: "across recent queries" },
  { label: "Rows inspected", value: "1.4M", detail: "across active analyses" },
];

export function AppPage() {
  const { isMobile, collapsed, mobileOpen, closeMobileSidebar, toggleSidebar } = useResponsiveSidebar();
  const {
    uploads,
    isUploading,
    deletingUploadId,
    error: uploadError,
    latestUploadMode,
    uploadFile,
    deleteUpload,
  } = useUpload();
  const {
    conversations,
    activeConversation,
    activeConversationId,
    loading,
    threadLoading,
    isSubmitting,
    error,
    startNewChat,
    selectConversation,
    sendPrompt,
  } = useChat();
  const inspection = useInspectionPanel();
  const [draft, setDraft] = useState("");
  const [activeSection, setActiveSection] = useState<SidebarSection>(() => uiStore.getActiveSection() as SidebarSection);
  const { activeUploads, removeActiveUpload } = useActiveUploads(uploads);

  const currentTitle = useMemo(() => {
    if (activeSection === "uploads") return "Data uploads";
    if (activeSection === "saved") return "Saved analyses";
    if (activeSection === "dashboards") return "Dashboards";
    return activeConversation?.title ?? "Planera workspace";
  }, [activeConversation?.title, activeSection]);

  const currentSubtitle = useMemo(() => {
    if (activeSection === "uploads") return "Profile incoming datasets before you ask the next question.";
    if (activeSection === "saved") return "Keep a reviewable archive of verified findings and reusable outputs.";
    if (activeSection === "dashboards") return "A compact operational view across recent Planera activity.";
    return "Chat with data, inspect the execution path, and keep the technical details one click away.";
  }, [activeSection]);

  const workspaceStatus = useMemo(() => {
    const hasAssistantMessage = activeConversation?.messages.some((message) => message.role === "assistant") ?? false;
    const hasDemoActivity = isDemoOnlyMode || (activeConversation?.mode === "demo" && hasAssistantMessage) || latestUploadMode === "demo";
    const hasLiveActivity = (activeConversation?.mode === "live" && hasAssistantMessage) || latestUploadMode === "live";

    if (isDemoOnlyMode) {
      return {
        connectionLabel: "Demo data source",
        connectionTone: "warning" as const,
        modeLabel: "Demo mode",
        modeTone: "warning" as const,
      };
    }

    return {
      connectionLabel: hasDemoActivity ? "Demo fallback active" : hasLiveActivity ? "Connected backend" : "Backend configured",
      connectionTone: hasDemoActivity ? ("warning" as const) : hasLiveActivity ? ("accent" as const) : ("neutral" as const),
      modeLabel: env.apiFallbackMode === "hybrid" ? "Hybrid mode" : "Live mode",
      modeTone: env.apiFallbackMode === "hybrid" ? ("neutral" as const) : ("success" as const),
    };
  }, [activeConversation?.messages, activeConversation?.mode, latestUploadMode]);

  const latestUploadLabel = useMemo(() => {
    if (!uploads[0]) return undefined;
    const prefix = latestUploadMode === "demo" ? "Demo" : "Uploaded";
    return `${prefix} ${uploads[0].type}`;
  }, [latestUploadMode, uploads]);

  const handleSectionChange = (section: SidebarSection) => {
    setActiveSection(section);
    uiStore.setActiveSection(section);
  };

  const handleChatUpload = async (file: File) => {
    try {
      await uploadFile(file);
      handleSectionChange("chats");
    } catch {
      // Upload errors are surfaced through the hook state and UI.
    }
  };

  const handleUploadsSectionUpload = async (file: File) => {
    try {
      await uploadFile(file);
      handleSectionChange("uploads");
    } catch {
      // Upload errors are surfaced through the hook state and UI.
    }
  };

  const handleSubmit = async () => {
    const success = await sendPrompt(draft, activeUploads);
    if (success) {
      setDraft("");
    }
    handleSectionChange("chats");
  };

  const chatView = (
    <div className="flex h-full min-h-0 min-w-0 flex-col overflow-hidden">
      <div className="scroll-fade min-h-0 min-w-0 flex-1 overflow-y-auto px-4 py-6 sm:px-6">
        <PageContainer className="max-w-4xl">
          {loading ? (
            <div className="flex items-center justify-center py-24">
              <div className="flex items-center gap-3 rounded-full border border-line bg-panel px-4 py-3 text-sm text-muted">
                <Spinner />
                Loading recent analyses
              </div>
            </div>
          ) : error ? (
            <ErrorState title="Unable to load workspace" description={error} />
          ) : (
            <ChatThread
              messages={activeConversation?.messages ?? []}
              isSubmitting={isSubmitting}
              isLoadingThread={threadLoading}
              onInspect={(inspectionId, preferredTab) => void inspection.openInspection(inspectionId, preferredTab)}
            />
          )}
        </PageContainer>
      </div>
      <ChatInput
        value={draft}
        onChange={setDraft}
        onSubmit={() => void handleSubmit()}
        onUpload={(file) => void handleChatUpload(file)}
        onRemoveAttachment={removeActiveUpload}
        attachments={activeUploads}
        isSubmitting={isSubmitting}
        isUploading={isUploading}
      />
    </div>
  );

  const uploadsView = (
    <UploadsPanel
      uploads={uploads}
      error={uploadError}
      isUploading={isUploading}
      deletingUploadId={deletingUploadId}
      onUpload={(file) => void handleUploadsSectionUpload(file)}
      onDelete={(assetId) => void deleteUpload(assetId)}
    />
  );

  const savedView = (
    <PageContainer className="min-w-0 space-y-6 px-4 py-6 sm:px-6">
      <div className="grid gap-4 lg:grid-cols-3">
        {savedAnalyses.map((analysis) => (
          <Card key={analysis.id} className="p-5">
            <div className="flex items-center justify-between gap-3">
              <h3 className="text-lg font-semibold text-ink">{analysis.title}</h3>
              <StatusBadge
                label={analysis.status}
                tone={analysis.status === "verified" ? "success" : analysis.status === "review" ? "warning" : "neutral"}
              />
            </div>
            <p className="mt-3 text-sm leading-7 text-muted">{analysis.summary}</p>
            <div className="mt-5">
              <Button variant="secondary" onClick={() => void inspection.openInspection("inspect_pipeline_drop")}>
                Review execution
              </Button>
            </div>
          </Card>
        ))}
      </div>
    </PageContainer>
  );

  const dashboardView = (
    <PageContainer className="min-w-0 space-y-6 px-4 py-6 sm:px-6">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {dashboardMetrics.map((metric) => (
          <Card key={metric.label} className="p-5">
            <p className="text-xs uppercase tracking-[0.14em] text-muted">{metric.label}</p>
            <p className="mt-3 text-3xl font-semibold text-ink">{metric.value}</p>
            <p className="mt-2 text-sm text-muted">{metric.detail}</p>
          </Card>
        ))}
      </div>
      <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
        <Card className="p-5">
          <p className="text-sm font-semibold text-ink">Recent highlights</p>
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            <InsightCard
              title="Inspection engagement is high"
              body="Recent runs opened the SQL drawer before the next prompt, which supports Planera’s human-in-the-loop design."
              tone="positive"
            />
            <InsightCard
              title="Uploads remain active"
              body={`${formatCompactNumber(uploads.reduce((count, item) => count + (item.rows ?? 0), 0))} rows are available across recent file uploads.`}
              tone="neutral"
            />
          </div>
        </Card>
        <Card className="p-5">
          <p className="text-sm font-semibold text-ink">Workspace note</p>
          <p className="mt-3 text-sm leading-7 text-muted">
            This dashboard is intentionally light. Planera keeps the center of gravity in the conversation and uses dashboards to summarize activity, not replace the chat-first workflow.
          </p>
        </Card>
      </div>
    </PageContainer>
  );

  return (
    <AppLayout
      sidebar={
        <Sidebar
          conversations={conversations}
          activeSection={activeSection}
          activeConversationId={activeConversationId}
          collapsed={collapsed}
          isMobile={isMobile}
          mobileOpen={mobileOpen}
          onSelectSection={handleSectionChange}
          onSelectConversation={(conversationId) => {
            selectConversation(conversationId);
            handleSectionChange("chats");
            closeMobileSidebar();
          }}
          onNewChat={() => {
            startNewChat();
            handleSectionChange("chats");
            closeMobileSidebar();
          }}
          onToggleCollapse={toggleSidebar}
          onCloseMobile={closeMobileSidebar}
        />
      }
      header={
        <AppHeader
          title={currentTitle}
          subtitle={currentSubtitle}
          uploadedLabel={latestUploadLabel}
          connectionLabel={workspaceStatus.connectionLabel}
          connectionTone={workspaceStatus.connectionTone}
          modeLabel={workspaceStatus.modeLabel}
          modeTone={workspaceStatus.modeTone}
          onToggleSidebar={toggleSidebar}
          showMenuButton={isMobile}
        />
      }
      inspectionPanel={
        <InspectionPanel
          open={inspection.open}
          loading={inspection.loading}
          error={inspection.error}
          inspection={inspection.inspection}
          activeTab={inspection.activeTab}
          onClose={inspection.closeInspection}
          onTabChange={inspection.setActiveTab}
        />
      }
    >
      {activeSection === "chats" ? chatView : null}
      {activeSection === "uploads" ? uploadsView : null}
      {activeSection === "saved" ? savedView : null}
      {activeSection === "dashboards" ? dashboardView : null}
      {!conversations.length && !loading && activeSection === "chats" ? (
        <PageContainer className="px-4 py-6 sm:px-6">
          <EmptyState title="No chats yet" description="Create a new conversation to begin." actionLabel="New chat" onAction={startNewChat} />
        </PageContainer>
      ) : null}
    </AppLayout>
  );
}
