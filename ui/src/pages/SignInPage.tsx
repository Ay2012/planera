import type { FormEvent } from "react";
import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { ApiError } from "@/api/client";
import { Button } from "@/components/shared/Button";
import { Card } from "@/components/shared/Card";
import { Input } from "@/components/shared/Input";
import { PageContainer } from "@/components/shared/PageContainer";
import { Spinner } from "@/components/shared/Spinner";
import { useAuth } from "@/hooks/useAuth";
import { MarketingLayout } from "@/layouts/MarketingLayout";

const signInHighlights = [
  {
    title: "Resume active threads",
    description: "Jump back into saved analyses, recent uploads, and the latest execution trail.",
  },
  {
    title: "Inspect every step",
    description: "Review the SQL path, validation notes, and trace output behind each answer.",
  },
  {
    title: "Share a single workspace",
    description: "Keep analysts, operators, and stakeholders aligned in one calm interface.",
  },
];

type AuthMode = "signin" | "signup";

export function SignInPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: string } | null)?.from ?? "/app";
  const { isReady, isAuthenticated, login, signUp } = useAuth();

  const [mode, setMode] = useState<AuthMode>("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isReady && isAuthenticated) {
      navigate(from, { replace: true });
    }
  }, [from, isAuthenticated, isReady, navigate]);

  const switchMode = (next: AuthMode) => {
    setMode(next);
    setError(null);
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!isReady || submitting) {
      return;
    }
    setError(null);
    setSubmitting(true);
    try {
      if (mode === "signin") {
        await login(email, password);
      } else {
        await signUp(email, password, displayName || null);
      }
      navigate(from, { replace: true });
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Something went wrong. Try again.";
      setError(message);
    } finally {
      setSubmitting(false);
    }
  };

  if (!isReady) {
    return (
      <MarketingLayout>
        <section className="relative overflow-hidden pb-20 pt-10 sm:pb-24 sm:pt-16">
          <PageContainer className="flex min-h-[50vh] items-center justify-center gap-3">
            <Spinner className="h-8 w-8 border-t-accent" />
            <p className="text-sm text-muted">Restoring session…</p>
          </PageContainer>
        </section>
      </MarketingLayout>
    );
  }

  return (
    <MarketingLayout>
      <section className="relative overflow-hidden pb-20 pt-10 sm:pb-24 sm:pt-16">
        <PageContainer className="relative">
          <div className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr] lg:items-center">
            <Card elevated className="relative overflow-hidden border-line/80 bg-elevated p-8 sm:p-10">
              <div className="absolute right-0 top-0 h-48 w-48 -translate-y-10 translate-x-10 rounded-full bg-accent-soft/80 blur-3xl" />
              <div className="relative">
                <p className="text-sm uppercase tracking-[0.18em] text-accent-strong">Secure Workspace Access</p>
                <h1 className="mt-4 max-w-xl text-4xl sm:text-5xl">Sign in and continue where the analysis left off.</h1>
                <p className="mt-5 max-w-2xl text-base leading-8 text-muted">
                  Planera keeps the experience grounded: one workspace for natural-language questions, inspection trails, and decisions your team can revisit with confidence.
                </p>

                <div className="mt-8 grid gap-3">
                  {signInHighlights.map((item) => (
                    <div key={item.title} className="rounded-[20px] border border-line/80 bg-panel/85 p-5">
                      <p className="text-sm font-semibold text-ink">{item.title}</p>
                      <p className="mt-2 text-sm leading-7 text-muted">{item.description}</p>
                    </div>
                  ))}
                </div>

                <div className="mt-8 rounded-[24px] border border-accent/15 bg-accent-soft/60 p-5">
                  <p className="text-xs uppercase tracking-[0.18em] text-accent-strong">Demo auth</p>
                  <p className="mt-3 text-sm leading-7 text-muted">
                    Email and password are stored in the local API (SQLite). Your session stays signed in across refreshes until you sign out.
                  </p>
                </div>
              </div>
            </Card>

            <Card elevated className="border-line/80 p-8 sm:p-10">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <p className="text-sm uppercase tracking-[0.16em] text-muted">{mode === "signin" ? "Welcome back" : "Create an account"}</p>
                  <h2 className="mt-3 text-3xl">{mode === "signin" ? "Sign in to Planera" : "Sign up for Planera"}</h2>
                </div>
                <span className="rounded-full bg-accent-soft px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] text-accent-strong">
                  Team access
                </span>
              </div>

              <div className="mt-6 flex flex-wrap gap-2">
                <Button
                  type="button"
                  variant={mode === "signin" ? "primary" : "secondary"}
                  size="md"
                  className="rounded-2xl"
                  onClick={() => switchMode("signin")}
                >
                  Sign in
                </Button>
                <Button
                  type="button"
                  variant={mode === "signup" ? "primary" : "secondary"}
                  size="md"
                  className="rounded-2xl"
                  onClick={() => switchMode("signup")}
                >
                  Sign up
                </Button>
              </div>

              <div className="mt-6 grid gap-3 sm:grid-cols-2">
                <Button type="button" variant="secondary" className="h-12 justify-start rounded-2xl px-4" disabled aria-disabled="true" title="Not available in this demo">
                  Continue with Google
                </Button>
                <Button type="button" variant="secondary" className="h-12 justify-start rounded-2xl px-4" disabled aria-disabled="true" title="Not available in this demo">
                  Continue with Microsoft
                </Button>
              </div>

              <div className="my-6 flex items-center gap-3 text-xs uppercase tracking-[0.16em] text-muted">
                <span className="h-px flex-1 bg-line" />
                <span>Email {mode === "signin" ? "sign in" : "registration"}</span>
                <span className="h-px flex-1 bg-line" />
              </div>

              {error ? (
                <div className="mb-4 rounded-2xl border border-danger/20 bg-danger-soft/80 px-4 py-3 text-sm text-danger" role="alert">
                  {error}
                </div>
              ) : null}

              <form className="space-y-4" onSubmit={handleSubmit}>
                <label className="block space-y-2 text-sm text-muted">
                  Work email
                  <Input
                    type="email"
                    name="email"
                    autoComplete="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="name@company.com"
                  />
                </label>

                {mode === "signup" ? (
                  <label className="block space-y-2 text-sm text-muted">
                    Display name <span className="font-normal text-muted/80">(optional)</span>
                    <Input
                      type="text"
                      name="displayName"
                      autoComplete="name"
                      value={displayName}
                      onChange={(e) => setDisplayName(e.target.value)}
                      placeholder="Ada Lovelace"
                    />
                  </label>
                ) : null}

                <label className="block space-y-2 text-sm text-muted">
                  Password
                  <Input
                    type="password"
                    name="password"
                    autoComplete={mode === "signin" ? "current-password" : "new-password"}
                    required
                    minLength={mode === "signup" ? 8 : undefined}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder={mode === "signup" ? "At least 8 characters" : "Enter your password"}
                  />
                </label>

                <Button type="submit" size="lg" fullWidth disabled={submitting}>
                  {submitting ? (
                    <span className="flex items-center justify-center gap-2">
                      <Spinner className="h-5 w-5 border-t-white" />
                      {mode === "signin" ? "Signing in…" : "Creating account…"}
                    </span>
                  ) : mode === "signin" ? (
                    "Sign In"
                  ) : (
                    "Create account"
                  )}
                </Button>
              </form>

              <div className="mt-6 flex flex-wrap items-center justify-between gap-3 text-sm text-muted">
                <Link to="/" className="transition hover:text-ink">
                  Back to home
                </Link>
              </div>
            </Card>
          </div>
        </PageContainer>
      </section>
    </MarketingLayout>
  );
}
