import type { FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Button } from "@/components/shared/Button";
import { Card } from "@/components/shared/Card";
import { Input } from "@/components/shared/Input";
import { PageContainer } from "@/components/shared/PageContainer";
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

export function SignInPage() {
  const navigate = useNavigate();

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    navigate("/app");
  };

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
                  <p className="text-xs uppercase tracking-[0.18em] text-accent-strong">Prototype Note</p>
                  <p className="mt-3 text-sm leading-7 text-muted">
                    This sign-in flow currently opens the workspace preview after submission, so the page is ready for a real auth integration later without changing the navigation.
                  </p>
                </div>
              </div>
            </Card>

            <Card elevated className="border-line/80 p-8 sm:p-10">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-sm uppercase tracking-[0.16em] text-muted">Welcome back</p>
                  <h2 className="mt-3 text-3xl">Sign in to Planera</h2>
                </div>
                <span className="rounded-full bg-accent-soft px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] text-accent-strong">
                  Team access
                </span>
              </div>

              <div className="mt-6 grid gap-3 sm:grid-cols-2">
                <Button variant="secondary" className="h-12 justify-start rounded-2xl px-4">
                  Continue with Google
                </Button>
                <Button variant="secondary" className="h-12 justify-start rounded-2xl px-4">
                  Continue with Microsoft
                </Button>
              </div>

              <div className="my-6 flex items-center gap-3 text-xs uppercase tracking-[0.16em] text-muted">
                <span className="h-px flex-1 bg-line" />
                <span>Or use email</span>
                <span className="h-px flex-1 bg-line" />
              </div>

              <form className="space-y-4" onSubmit={handleSubmit}>
                <label className="block space-y-2 text-sm text-muted">
                  Work email
                  <Input type="email" name="email" placeholder="name@company.com" autoComplete="email" required />
                </label>

                <label className="block space-y-2 text-sm text-muted">
                  Password
                  <Input type="password" name="password" placeholder="Enter your password" autoComplete="current-password" required />
                </label>

                <div className="flex flex-wrap items-center justify-between gap-3 text-sm">
                  <label className="flex items-center gap-2 text-muted">
                    <input
                      type="checkbox"
                      name="remember"
                      className="h-4 w-4 rounded border-line bg-panel text-accent focus:ring-accent/30"
                    />
                    Keep me signed in
                  </label>
                  <Link to="/" className="text-accent-strong transition hover:text-accent">
                    Need an invite?
                  </Link>
                </div>

                <Button type="submit" size="lg" fullWidth>
                  Sign In
                </Button>
              </form>

              <div className="mt-6 flex flex-wrap items-center justify-between gap-3 text-sm text-muted">
                <Link to="/" className="transition hover:text-ink">
                  Back to home
                </Link>
                <Link to="/app" className="text-accent-strong transition hover:text-accent">
                  Skip to workspace
                </Link>
              </div>
            </Card>
          </div>
        </PageContainer>
      </section>
    </MarketingLayout>
  );
}
