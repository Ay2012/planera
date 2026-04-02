import { PageContainer } from "@/components/shared/PageContainer";

const brands = ["Northstar Capital", "Waypoint Ops", "Meridian Cloud", "Arbor Labs", "Summit Commerce"];

export function TrustStrip() {
  return (
    <section className="pb-12">
      <PageContainer>
        <div className="rounded-[30px] border border-line bg-panel px-6 py-8 shadow-card">
          <p className="text-center text-xs uppercase tracking-[0.18em] text-muted">
            Built for modern analytics teams and designed for trustworthy analysis
          </p>
          <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
            {brands.map((brand) => (
              <div key={brand} className="rounded-2xl border border-line bg-surface px-4 py-4 text-center text-sm font-medium text-ink">
                {brand}
              </div>
            ))}
          </div>
        </div>
      </PageContainer>
    </section>
  );
}
