import { Link } from "react-router-dom";
import { Input } from "@/components/shared/Input";
import { Button } from "@/components/shared/Button";
import { Card } from "@/components/shared/Card";
import { PageContainer } from "@/components/shared/PageContainer";
import { env } from "@/config/env";

export function SettingsPage() {
  return (
    <div className="min-h-screen bg-canvas py-12">
      <PageContainer className="max-w-3xl">
        <div className="mb-8 flex items-center justify-between gap-4">
          <div>
            <p className="text-sm uppercase tracking-[0.16em] text-muted">Settings</p>
            <h1 className="mt-2 text-4xl">Workspace preferences</h1>
          </div>
          <Link to="/app">
            <Button variant="secondary">Back to app</Button>
          </Link>
        </div>

        <div className="space-y-5">
          <Card className="p-6">
            <h2 className="text-lg font-semibold text-ink">Workspace details</h2>
            <div className="mt-5 grid gap-4 md:grid-cols-2">
              <label className="space-y-2 text-sm text-muted">
                Workspace name
                <Input defaultValue="Planera Demo Workspace" />
              </label>
              <label className="space-y-2 text-sm text-muted">
                Default analyst mode
                <Input defaultValue="Explain answers with inspection trail" />
              </label>
            </div>
          </Card>

          <Card className="p-6">
            <h2 className="text-lg font-semibold text-ink">Backend configuration</h2>
            <div className="mt-5 space-y-4">
              <label className="space-y-2 text-sm text-muted">
                API base URL
                <Input value={env.apiBaseUrl} readOnly />
              </label>
              <label className="space-y-2 text-sm text-muted">
                Fallback mode
                <Input value={env.apiFallbackMode} readOnly />
              </label>
            </div>
          </Card>
        </div>
      </PageContainer>
    </div>
  );
}
