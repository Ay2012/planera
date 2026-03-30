import { PageContainer } from "@/components/shared/PageContainer";
import { Card } from "@/components/shared/Card";
import { homepageFeatureCards } from "@/lib/constants";

export function FeatureGrid() {
  return (
    <section className="py-20">
      <PageContainer>
        <div className="grid gap-8 lg:grid-cols-[0.82fr_1.18fr] lg:items-start">
          <div className="max-w-xl">
            <p className="text-sm font-medium uppercase tracking-[0.18em] text-muted">Product features</p>
            <h2 className="mt-4 text-4xl sm:text-5xl">Designed for clarity, not dashboard sprawl.</h2>
            <p className="mt-5 text-lg leading-8 text-muted">
              Planera combines chat-first usability with the kind of technical transparency analysts need when business decisions depend on the answer.
            </p>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            {homepageFeatureCards.map((feature) => (
              <Card key={feature.title} className="p-6">
                <h3 className="text-xl">{feature.title}</h3>
                <p className="mt-3 text-sm leading-7 text-muted">{feature.description}</p>
              </Card>
            ))}
          </div>
        </div>
      </PageContainer>
    </section>
  );
}
