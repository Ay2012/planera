"""Constants used across the application."""

SUPPORTED_INTENTS = {"diagnosis", "comparison", "recommendation"}
SUPPORTED_METRICS = {"pipeline_velocity"}
SUPPORTED_DIMENSIONS = {"segment", "stage", "owner", "deal_age_bucket", "plan_tier"}
PRIMARY_METRIC = "pipeline_velocity"

PIPELINE_METRIC_KEYWORDS = (
    "pipeline velocity",
    "sales cycle",
    "deal stagnation",
    "pipeline",
    "velocity",
)

SAMPLE_QUESTIONS = [
    "Why did pipeline velocity drop this week?",
    "Compare SMB vs Enterprise performance",
    "Which segment is underperforming?",
    "What should we do about this drop?",
    "Which deals should we prioritize?",
]

VALID_STAGES = ["Stage 1", "Stage 2", "Stage 3", "Negotiation", "Closed Won", "Closed Lost"]
VALID_SEGMENTS = ["SMB", "Mid-Market", "Enterprise"]
VALID_PLAN_TIERS = ["Starter", "Growth", "Enterprise"]
