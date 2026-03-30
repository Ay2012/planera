import { Card } from "@/components/shared/Card";
import { PageContainer } from "@/components/shared/PageContainer";

const steps = [
  {
    number: "01",
    title: "Ask a question",
    description: "Start with plain language. Planera translates business questions into a structured analytical plan.",
  },
  {
    number: "02",
    title: "Connect or upload data",
    description: "Point the workspace at a database or bring in CSV and TSV files for quick analysis.",
  },
  {
    number: "03",
    title: "Run analysis",
    description: "Planera explores the data, executes queries, tracks filters, and prepares technical detail behind the scenes.",
  },
  {
    number: "04",
    title: "Get verified insights",
    description: "Review the answer, inspect the SQL, and move forward with traceable next actions instead of opaque output.",
  },
];

export function HowItWorks() {
  return (
    <section className="py-20" id="how-it-works">
      <PageContainer>
        <div className="max-w-2xl">
          <p className="text-sm font-medium uppercase tracking-[0.18em] text-muted">How it works</p>
          <h2 className="mt-4 text-4xl sm:text-5xl">A calmer path from question to conclusion.</h2>
          <p className="mt-5 text-lg leading-8 text-muted">
            The workflow is intentionally simple on the surface and rigorous underneath, so teams can move quickly without giving up analytical trust.
          </p>
        </div>
        <div className="mt-10 grid gap-4 lg:grid-cols-4">
          {steps.map((step) => (
            <Card key={step.number} className="p-6">
              <p className="text-sm font-medium uppercase tracking-[0.16em] text-muted">{step.number}</p>
              <h3 className="mt-6 text-2xl">{step.title}</h3>
              <p className="mt-4 text-sm leading-7 text-muted">{step.description}</p>
            </Card>
          ))}
        </div>
      </PageContainer>
    </section>
  );
}
