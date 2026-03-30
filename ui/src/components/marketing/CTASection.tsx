import { Link } from "react-router-dom";
import { Button } from "@/components/shared/Button";
import { Card } from "@/components/shared/Card";
import { PageContainer } from "@/components/shared/PageContainer";

export function CTASection() {
  return (
    <section className="py-20" id="pricing">
      <PageContainer>
        <Card elevated className="overflow-hidden rounded-[34px] bg-hero-glow p-8 sm:p-12">
          <div className="max-w-2xl">
            <p className="text-sm font-medium uppercase tracking-[0.18em] text-muted">Ready to explore Planera</p>
            <h2 className="mt-4 text-4xl sm:text-5xl">Bring calm, transparent analytics into the flow of work.</h2>
            <p className="mt-5 text-lg leading-8 text-muted">
              Open the workspace, ask a real question, inspect the execution, and see how Planera turns analysis into an interactive product surface.
            </p>
            <div className="mt-8">
              <Link to="/app">
                <Button size="lg">Open App</Button>
              </Link>
            </div>
          </div>
        </Card>
      </PageContainer>
    </section>
  );
}
