import { useState } from "react";
import { Link } from "react-router-dom";
import { Button } from "@/components/shared/Button";
import { Card } from "@/components/shared/Card";
import { Modal } from "@/components/shared/Modal";
import { PageContainer } from "@/components/shared/PageContainer";
import { StatusBadge } from "@/components/app/StatusBadge";

export function HeroSection() {
  const [demoOpen, setDemoOpen] = useState(false);

  return (
    <section className="pb-20 pt-14 sm:pb-24 sm:pt-20" id="product">
      <PageContainer className="max-w-[1400px]">
        <div className="grid gap-10 lg:grid-cols-[minmax(320px,0.8fr)_minmax(0,1.2fr)] lg:items-center xl:grid-cols-[minmax(340px,0.74fr)_minmax(0,1.26fr)]">
          <div className="max-w-2xl">
            <p className="inline-flex rounded-full border border-line bg-panel px-4 py-2 text-xs font-medium uppercase tracking-[0.16em] text-muted shadow-card">
              Calm analytics for serious teams
            </p>
            <h1 className="mt-7 max-w-4xl text-balance text-5xl leading-[1.02] sm:text-6xl lg:text-7xl">
              Turn business questions into transparent answers, not analyst bottlenecks.
            </h1>
            <p className="mt-7 max-w-2xl text-lg leading-8 text-muted sm:text-xl">
              Planera helps teams chat with data, inspect the exact work behind every answer, and move from question to verified insight in a single premium workspace.
            </p>
            <div className="mt-10 flex flex-wrap gap-3">
              <Link to="/app">
                <Button size="lg">Try Planera</Button>
              </Link>
              <Button size="lg" variant="secondary" onClick={() => setDemoOpen(true)}>
                See Demo
              </Button>
            </div>
            <div className="mt-10 flex flex-wrap gap-3">
              <StatusBadge label="Natural-language analytics" tone="accent" />
              <StatusBadge label="SQL inspection" tone="neutral" />
              <StatusBadge label="Verified workflows" tone="success" />
            </div>
          </div>

          <Card elevated className="w-full overflow-hidden rounded-[30px] bg-white/95 p-5">
            <div className="rounded-[26px] border border-line bg-surface p-4">
              <div className="flex items-center justify-between border-b border-line pb-4">
                <div>
                  <p className="text-sm font-semibold text-ink">Planera workspace</p>
                  <p className="mt-1 text-xs text-muted">Chat-first analytics with visible execution detail</p>
                </div>
                <StatusBadge label="Connected warehouse" tone="accent" />
              </div>

              <div className="mt-5 grid gap-4 lg:grid-cols-[minmax(0,1.42fr)_minmax(300px,0.88fr)] xl:grid-cols-[minmax(0,1.5fr)_minmax(320px,0.84fr)]">
                <div className="min-w-0 space-y-3">
                  <div className="rounded-[22px] bg-ink px-4 py-3 text-sm text-white shadow-card">
                    Why is enterprise conversion softening this month?
                  </div>
                  <div className="min-w-0 rounded-[22px] border border-line bg-panel px-4 py-4 shadow-card">
                    <div className="flex items-center gap-2">
                      <span className="flex h-8 w-8 items-center justify-center rounded-2xl bg-accent text-xs font-semibold text-white">P</span>
                      <span className="text-sm font-semibold text-ink">Planera</span>
                      <StatusBadge label="Verified" tone="success" />
                    </div>
                    <p className="mt-3 text-sm leading-7 text-ink">
                      Enterprise conversion is down 5.2 points versus the prior comparison window, with the largest weakness showing up in late-stage review.
                    </p>
                    <div className="mt-4 grid grid-cols-[repeat(3,minmax(0,1fr))] gap-3">
                      {[
                        ["Runtime", "814 ms"],
                        ["Rows", "3"],
                        ["Confidence", "92%"],
                      ].map(([label, value]) => (
                        <div key={label} className="min-w-0 overflow-hidden rounded-2xl bg-surface px-3 py-3">
                          <p className="min-w-0 whitespace-nowrap text-[10px] uppercase leading-tight tracking-[0.08em] text-muted sm:text-[11px]">
                            {label}
                          </p>
                          <p className="mt-2 text-sm font-semibold text-ink">{value}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="min-w-0 space-y-3">
                  <div className="rounded-[22px] border border-line bg-panel shadow-card">
                    <div className="border-b border-line px-4 py-3">
                      <p className="text-sm font-semibold text-ink">Inspection</p>
                      <p className="text-xs text-muted">Structured execution detail</p>
                    </div>
                    <div className="space-y-3 p-4">
                      <div className="flex flex-wrap gap-2">
                        <StatusBadge label="Query valid" tone="success" />
                        <StatusBadge label="Snowflake" tone="accent" />
                      </div>
                      <div className="rounded-2xl bg-[#12161A] p-3 font-mono text-[11px] leading-6 text-[#E8F0EB]">
                        SELECT segment, AVG(conversion_rate)
                        <br />
                        FROM revenue_pipeline
                        <br />
                        WHERE snapshot_date &gt;= CURRENT_DATE - 14
                      </div>
                      <div className="rounded-2xl bg-surface p-3">
                        <p className="text-[11px] uppercase tracking-[0.14em] text-muted">Validation</p>
                        <p className="mt-2 text-sm text-ink">Metric consistency checks passed before the narrative was generated.</p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </Card>
        </div>
      </PageContainer>

      <Modal open={demoOpen} onClose={() => setDemoOpen(false)} title="Planera demo">
        <div className="grid gap-6 md:grid-cols-2">
          <Card className="p-5">
            <p className="text-sm font-semibold text-ink">Conversation-first workflow</p>
            <p className="mt-3 text-sm leading-7 text-muted">
              Planera keeps the user in a calm chat interface while still surfacing metrics, result previews, and recommendations inline.
            </p>
          </Card>
          <Card className="p-5">
            <p className="text-sm font-semibold text-ink">Inspectable execution</p>
            <p className="mt-3 text-sm leading-7 text-muted">
              Every answer can open into a structured review surface with SQL, results, trace, and validation so analysts stay in the loop.
            </p>
          </Card>
        </div>
      </Modal>
    </section>
  );
}
