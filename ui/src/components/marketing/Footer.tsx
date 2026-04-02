import { Link } from "react-router-dom";
import { PageContainer } from "@/components/shared/PageContainer";

export function Footer() {
  return (
    <footer className="border-t border-line/80 py-8">
      <PageContainer className="flex flex-col gap-4 text-sm text-muted sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="font-semibold text-ink">Planera</p>
          <p className="mt-1">Premium analytics copilot for transparent decision-making.</p>
        </div>
        <div className="flex flex-wrap gap-5">
          <a href="#product">Product</a>
          <a href="#how-it-works">How it Works</a>
          <a href="#use-cases">Use Cases</a>
          <Link to="/app">Open App</Link>
        </div>
      </PageContainer>
    </footer>
  );
}
