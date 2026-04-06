import { Link } from "react-router-dom";
import { Button } from "@/components/shared/Button";
import { Card } from "@/components/shared/Card";
import { PageContainer } from "@/components/shared/PageContainer";
import { classNames } from "@/lib/classNames";

const pricingPlans = [
  {
    name: "Free",
    label: "Explore Planera",
    description:
      "For individuals who want to try the workspace, test a few real questions, and get a feel for the product before upgrading.",
    price: "$0",
    cadence: "no credit card required",
    cta: "Try Free",
    href: "/app",
    note: "Includes one editor seat, one workspace, and a light monthly usage allowance.",
    featured: false,
    features: [
      "Natural-language analytics for early exploration",
      "CSV and JSON uploads with inspection detail",
      "Saved conversations and result previews",
      "Community support and upgrade-ready workspace history",
    ],
  },
  {
    name: "Starter",
    label: "Self-serve",
    description:
      "For founders and operators who need clear answers fast without committing to a heavyweight analytics stack.",
    price: "$39",
    cadence: "per editor / month",
    cta: "Start with Starter",
    href: "/app",
    note: "Includes 3 collaborators and one shared workspace.",
    featured: false,
    features: [
      "Natural-language analysis and file uploads",
      "Saved chats, result exports, and SQL inspection",
      "Weekly summary digests for recurring questions",
      "Email support with 2-business-day response time",
    ],
  },
  {
    name: "Enterprise",
    label: "Governed rollout",
    description:
      "For security-conscious organizations rolling Planera out across departments, regions, or regulated workflows.",
    price: "Custom",
    cadence: "annual plans with tailored onboarding",
    cta: "Plan Enterprise Rollout",
    href: "/sign-in",
    note: "Built for procurement, security review, and long-term adoption.",
    featured: false,
    features: [
      "SSO, audit trails, and advanced workspace controls",
      "Private deployment options and network restrictions",
      "Dedicated success planning and training sessions",
      "Security review support and volume pricing",
    ],
  },
] as const;

export function PricingSection() {
  return (
    <section className="py-20" id="pricing">
      <PageContainer>
        <div
          className="overflow-hidden rounded-[36px] border border-line bg-panel px-6 py-8 shadow-soft sm:px-8 sm:py-10 lg:px-10"
          style={{
            backgroundImage:
              "radial-gradient(circle at top right, rgba(35, 88, 82, 0.14), transparent 30%), linear-gradient(180deg, rgba(255, 253, 249, 0.96), rgba(247, 242, 234, 0.92))",
          }}
        >
          <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(320px,0.46fr)] lg:items-end">
            <div className="max-w-3xl">
              <p className="text-sm font-medium uppercase tracking-[0.18em] text-muted">Pricing</p>
              <h2 className="mt-4 text-4xl sm:text-5xl">Three ways to bring calm, inspectable analytics into the team.</h2>
              <p className="mt-5 max-w-2xl text-lg leading-8 text-muted">
                Every plan keeps the conversation-first experience and execution visibility intact. The difference is how much collaboration,
                governance, and rollout support you want around it.
              </p>
            </div>

            <Card className="rounded-[28px] border-white/70 bg-white/70 p-6 backdrop-blur">
              <p className="text-xs font-medium uppercase tracking-[0.18em] text-muted">All paid plans include</p>
              <div className="mt-4 grid gap-3 sm:grid-cols-3 lg:grid-cols-1">
                {[
                  ["Unlimited viewers", "Share answers widely without paying for every stakeholder seat."],
                  ["Inspect every answer", "Open SQL, validation, and result metadata from the same workspace."],
                  ["Fast onboarding", "Start in days with guided setup instead of a long BI migration."],
                ].map(([title, body]) => (
                  <div key={title} className="rounded-[22px] border border-line/80 bg-panel/80 p-4">
                    <p className="text-sm font-semibold text-ink">{title}</p>
                    <p className="mt-2 text-sm leading-6 text-muted">{body}</p>
                  </div>
                ))}
              </div>
            </Card>
          </div>

          <div className="mt-10 grid gap-4 xl:grid-cols-3">
            {pricingPlans.map((plan) => (
              <Card
                key={plan.name}
                elevated
                className={classNames(
                  "flex h-full flex-col rounded-[30px] p-7 sm:p-8",
                  plan.featured ? "border-ink bg-ink text-white" : "bg-panel/85 backdrop-blur",
                )}
              >
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p
                      className={classNames(
                        "text-xs font-medium uppercase tracking-[0.18em]",
                        plan.featured ? "text-white/70" : "text-muted",
                      )}
                    >
                      {plan.label}
                    </p>
                    <h3 className={classNames("mt-4 text-3xl", plan.featured ? "text-white" : "text-ink")}>{plan.name}</h3>
                  </div>
                  {plan.featured ? (
                    <span className="rounded-full border border-white/20 bg-white/10 px-3 py-1 text-xs font-medium uppercase tracking-[0.16em] text-white">
                      Popular
                    </span>
                  ) : null}
                </div>

                <p className={classNames("mt-4 text-sm leading-7", plan.featured ? "text-white/72" : "text-muted")}>{plan.description}</p>

                <div className="mt-8 flex items-end gap-3">
                  <span className={classNames("text-5xl leading-none", plan.featured ? "text-white" : "text-ink")}>{plan.price}</span>
                  <span className={classNames("pb-1 text-sm", plan.featured ? "text-white/72" : "text-muted")}>{plan.cadence}</span>
                </div>

                <p className={classNames("mt-3 text-sm leading-6", plan.featured ? "text-white/72" : "text-muted")}>{plan.note}</p>

                <Link className="mt-8 block" to={plan.href}>
                  <Button
                    fullWidth
                    size="lg"
                    variant={plan.featured ? "secondary" : "primary"}
                    className={classNames(plan.featured ? "border-white/15 bg-white text-ink hover:bg-white/90" : undefined)}
                  >
                    {plan.cta}
                  </Button>
                </Link>

                <div className={classNames("mt-8 border-t pt-6", plan.featured ? "border-white/10" : "border-line")}>
                  <p className={classNames("text-xs font-medium uppercase tracking-[0.18em]", plan.featured ? "text-white/70" : "text-muted")}>
                    What&apos;s included
                  </p>
                  <ul className="mt-4 space-y-3">
                    {plan.features.map((feature) => (
                      <li key={feature} className="flex items-start gap-3">
                        <span
                          className={classNames(
                            "mt-[9px] h-2.5 w-2.5 flex-none rounded-full",
                            plan.featured ? "bg-white" : "bg-accent",
                          )}
                        />
                        <span className={classNames("text-sm leading-6", plan.featured ? "text-white/82" : "text-ink")}>{feature}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </Card>
            ))}
          </div>

          <div className="mt-6 flex flex-wrap items-center gap-3 text-sm text-muted">
            <span className="rounded-full border border-line bg-panel/80 px-4 py-2">Usage-based warehouse compute can be layered onto any plan.</span>
            <span className="rounded-full border border-line bg-panel/80 px-4 py-2">Annual commitments unlock 15% savings and guided rollout support.</span>
          </div>
        </div>
      </PageContainer>
    </section>
  );
}
