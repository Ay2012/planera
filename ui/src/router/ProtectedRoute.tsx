import type { PropsWithChildren } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { Spinner } from "@/components/shared/Spinner";
import { useAuth } from "@/hooks/useAuth";

export function ProtectedRoute({ children }: PropsWithChildren) {
  const { isReady, isAuthenticated } = useAuth();
  const location = useLocation();

  if (!isReady) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-3 bg-canvas text-muted">
        <Spinner className="h-8 w-8 border-t-accent" />
        <p className="text-sm">Loading session…</p>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/sign-in" replace state={{ from: location.pathname }} />;
  }

  return <>{children}</>;
}
