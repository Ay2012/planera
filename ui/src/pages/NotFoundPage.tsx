import { Link } from "react-router-dom";
import { Button } from "@/components/shared/Button";
import { EmptyState } from "@/components/shared/EmptyState";
import { PageContainer } from "@/components/shared/PageContainer";

export function NotFoundPage() {
  return (
    <div className="min-h-screen bg-canvas py-20">
      <PageContainer className="max-w-3xl">
        <EmptyState
          title="This page drifted out of scope"
          description="The route you requested does not exist in the current Planera frontend."
          actionLabel="Return home"
          onAction={() => window.location.assign("/")}
        />
        <div className="mt-4 flex justify-center">
          <Link to="/app">
            <Button variant="secondary">Open workspace</Button>
          </Link>
        </div>
      </PageContainer>
    </div>
  );
}
