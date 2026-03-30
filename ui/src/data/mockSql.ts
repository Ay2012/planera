import type { ResultTableData } from "@/types/inspection";

export const sqlLibrary = {
  pipeline: `WITH current_window AS (
  SELECT segment, AVG(conversion_rate) AS conversion_rate
  FROM revenue_pipeline
  WHERE snapshot_date >= CURRENT_DATE - INTERVAL '14 day'
  GROUP BY 1
),
prior_window AS (
  SELECT segment, AVG(conversion_rate) AS conversion_rate
  FROM revenue_pipeline
  WHERE snapshot_date BETWEEN CURRENT_DATE - INTERVAL '28 day' AND CURRENT_DATE - INTERVAL '14 day'
  GROUP BY 1
)
SELECT
  c.segment,
  ROUND(c.conversion_rate * 100, 1) AS current_conversion_pct,
  ROUND(p.conversion_rate * 100, 1) AS prior_conversion_pct,
  ROUND((c.conversion_rate - p.conversion_rate) * 100, 1) AS delta_pct
FROM current_window c
LEFT JOIN prior_window p USING (segment)
ORDER BY delta_pct ASC;`,
  churn: `SELECT
  segment,
  ROUND(AVG(churn_rate) * 100, 1) AS churn_pct,
  ROUND(AVG(expansion_mrr), 0) AS avg_expansion_mrr,
  COUNT(*) AS accounts
FROM subscription_health
WHERE snapshot_month >= DATE_TRUNC('quarter', CURRENT_DATE)
GROUP BY 1
ORDER BY churn_pct DESC;`,
  anomalies: `SELECT
  metric_name,
  anomaly_score,
  current_value,
  baseline_value,
  observed_at
FROM metric_anomalies
WHERE observed_at >= CURRENT_DATE - INTERVAL '7 day'
ORDER BY anomaly_score DESC
LIMIT 8;`,
  finance: `SELECT
  region,
  ROUND(SUM(actual_revenue), 0) AS actual_revenue,
  ROUND(SUM(plan_revenue), 0) AS plan_revenue,
  ROUND(SUM(actual_revenue - plan_revenue), 0) AS variance
FROM finance_forecast_q2
GROUP BY 1
ORDER BY variance ASC;`,
} as const;

export const resultTableLibrary: Record<keyof typeof sqlLibrary, ResultTableData> = {
  pipeline: {
    columns: ["segment", "current_conversion_pct", "prior_conversion_pct", "delta_pct"],
    rows: [
      { segment: "Enterprise", current_conversion_pct: 17.2, prior_conversion_pct: 22.4, delta_pct: -5.2 },
      { segment: "Mid-market", current_conversion_pct: 23.1, prior_conversion_pct: 25.6, delta_pct: -2.5 },
      { segment: "SMB", current_conversion_pct: 28.9, prior_conversion_pct: 29.6, delta_pct: -0.7 },
    ],
  },
  churn: {
    columns: ["segment", "churn_pct", "avg_expansion_mrr", "accounts"],
    rows: [
      { segment: "SMB", churn_pct: 6.1, avg_expansion_mrr: 1220, accounts: 408 },
      { segment: "Mid-market", churn_pct: 3.9, avg_expansion_mrr: 3810, accounts: 191 },
      { segment: "Enterprise", churn_pct: 1.8, avg_expansion_mrr: 11640, accounts: 54 },
    ],
  },
  anomalies: {
    columns: ["metric_name", "anomaly_score", "current_value", "baseline_value", "observed_at"],
    rows: [
      { metric_name: "Checkout conversion", anomaly_score: 0.94, current_value: 2.7, baseline_value: 3.8, observed_at: "2026-03-24" },
      { metric_name: "Activation day-7", anomaly_score: 0.88, current_value: 41.3, baseline_value: 47.2, observed_at: "2026-03-23" },
      { metric_name: "Refund rate", anomaly_score: 0.77, current_value: 1.9, baseline_value: 1.1, observed_at: "2026-03-22" },
    ],
  },
  finance: {
    columns: ["region", "actual_revenue", "plan_revenue", "variance"],
    rows: [
      { region: "North America", actual_revenue: 4220000, plan_revenue: 4550000, variance: -330000 },
      { region: "EMEA", actual_revenue: 3090000, plan_revenue: 3180000, variance: -90000 },
      { region: "APAC", actual_revenue: 2650000, plan_revenue: 2490000, variance: 160000 },
    ],
  },
};
