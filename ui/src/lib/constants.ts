export const homeNavLinks = [
  { label: "Product", href: "#product" },
  { label: "How it Works", href: "#how-it-works" },
  { label: "Use Cases", href: "#use-cases" },
  { label: "Pricing", href: "#pricing" },
  { label: "Sign In", href: "/app" },
] as const;

export const promptSuggestions = [
  "Why is pipeline conversion dropping?",
  "Show churn by segment",
  "Summarize top anomalies",
  "Generate SQL for this question",
];

export const sidebarNavItems = [
  { id: "chats", label: "Chats" },
  { id: "uploads", label: "Uploads" },
  { id: "saved", label: "Saved Analyses" },
  { id: "dashboards", label: "Dashboards" },
] as const;

export const homepageFeatureCards = [
  {
    title: "Natural-language analytics",
    description: "Turn a question into a structured plan, query path, and grounded explanation in one calm workspace.",
  },
  {
    title: "SQL inspection",
    description: "Open the exact SQL or query operations behind each answer without leaving the conversation.",
  },
  {
    title: "Traceable results",
    description: "Follow the execution flow, filters, result metadata, and trace checkpoints with confidence.",
  },
  {
    title: "Business-friendly insights",
    description: "Receive concise takeaways, next actions, and narrative context that stakeholders can understand quickly.",
  },
  {
    title: "Fast exploration",
    description: "Iterate on new questions without rebuilding a notebook or waiting on manual analyst workflows.",
  },
  {
    title: "Data upload and profiling",
    description: "Bring CSV, TSV, and database data into the workflow and see freshness, shape, and quality at a glance.",
  },
  {
    title: "Execution transparency",
    description: "Review runtime, row counts, filters, data source information, and query status in an inspection drawer.",
  },
  {
    title: "Validation summaries",
    description: "Check verification status, confidence signals, and result consistency before acting on an insight.",
  },
] as const;
