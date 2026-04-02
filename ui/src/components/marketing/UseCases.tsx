import { Card } from "@/components/shared/Card";
import { PageContainer } from "@/components/shared/PageContainer";

const useCases = [
  {
    title: "GTM analytics",
    description: "Understand pipeline shifts, segment performance, campaign efficiency, and growth motion without stitching together separate tools.",
  },
  {
    title: "Finance analysis",
    description: "Explain variance, summarize plan vs actuals, and inspect the logic behind sensitive reporting questions before sharing them.",
  },
  {
    title: "Product analytics",
    description: "Explore retention, activation, anomaly detection, and behavioral signals while preserving the technical path to each answer.",
  },
  {
    title: "Operations reporting",
    description: "Surface bottlenecks, process drift, and operational gaps across support, supply, or internal systems with clear next actions.",
  },
];

export function UseCases() {
  return (
    <section className="py-20" id="use-cases">
      <PageContainer>
        <div className="max-w-2xl">
          <p className="text-sm font-medium uppercase tracking-[0.18em] text-muted">Use cases</p>
          <h2 className="mt-4 text-4xl sm:text-5xl">Flexible enough for every analytics team.</h2>
        </div>
        <div className="mt-10 grid gap-4 md:grid-cols-2">
          {useCases.map((useCase) => (
            <Card key={useCase.title} className="p-6">
              <h3 className="text-2xl">{useCase.title}</h3>
              <p className="mt-4 text-sm leading-7 text-muted">{useCase.description}</p>
            </Card>
          ))}
        </div>
      </PageContainer>
    </section>
  );
}
