# GTM Analytics Copilot

GTM Analytics Copilot is an agentic analytics MVP for GTM teams. It takes a business question like "Why did pipeline velocity drop this week?", asks Gemini to plan the next exact analytical step, executes that step over the dataset, replans on failure, verifies the final metric deterministically, and returns a business-ready answer with a tactical next step.

## Why This Is Not "Chat With CSV"

This project is intentionally constrained:

- It uses an LLM planner, but only over curated dataset views.
- It does not let the model access arbitrary files or external systems.
- It executes exact SQL or restricted pandas steps instead of vague chain-of-thought.
- It replans using execution errors instead of silently falling back to rules.
- It verifies the headline metric before narration.
- It exposes every step, code snippet, and output preview in the UI.

That makes it feel much closer to a production analytics copilot than a generic chatbot sitting on top of a CSV file.

## MVP Scope

Supported intents:

- `diagnosis`
- `comparison`
- `recommendation`

Supported metric:

- `pipeline_velocity`

Supported dimensions:

- `segment`
- `stage`
- `owner`
- `deal_age_bucket`
- `plan_tier`

Out of scope:

- churn analytics for the current dataset
- CRM writes
- forecasting
- causal inference
- broad BI workflows

## Architecture

Backend:

- FastAPI for API contracts
- LangGraph for the planner-executor-replanner loop
- DuckDB plus pandas over the provided CRM sales dataset
- Gemini for planning, synthesis, and recommendation generation

Workflow:

1. Load curated semantic views from the CRM dataset
2. Ask Gemini for the next exact executable step
3. Execute that SQL or pandas step
4. If the step fails, send the error back to Gemini for replanning
5. Loop until Gemini signals the investigation is complete
6. Verify the headline pipeline metric deterministically
7. Ask Gemini to synthesize the answer from verified evidence only
8. Return trace, executed steps, evidence, and verification status

Core modules:

- `app/data/semantic_model.py`: curated dataset views and schema manifest
- `app/llm/gemini.py`: Gemini API wrapper
- `app/agent/planner.py`: Gemini next-step planning
- `app/agent/executor.py`: SQL and pandas execution engine
- `app/agent/reviewer.py`: retry and replan routing
- `app/agent/graph.py`: LangGraph loop orchestration
- `app/api/routes.py`: API surface
- `ui/streamlit_app.py`: agent-trace demo UI

## Repo Structure

```text
gtm-copilot/
├── app/
├── ui/
├── data/
├── tests/
├── .env.example
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## Setup

### 1. Create the environment

```bash
cd gtm-copilot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### 2. Run the API

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API endpoints:

- `GET /health`
- `GET /sample-questions`
- `POST /analyze`

Example request:

```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"query":"Why did pipeline velocity drop this week?"}'
```

### 3. Run the Streamlit UI

In a second terminal:

```bash
streamlit run ui/streamlit_app.py
```

## Environment Variables

Defined in `.env.example`:

- `APP_NAME`
- `APP_ENV`
- `API_HOST`
- `API_PORT`
- `STREAMLIT_PORT`
- `GEMINI_API_KEY`
- `GEMINI_MODEL`
- `LOG_LEVEL`
- `API_BASE_URL`

`GEMINI_API_KEY` is required. This version does not include a non-LLM fallback path.

## Data Model

Current dataset:

- `data/CRM+Sales+Opportunities/sales_pipeline.csv`
- `data/CRM+Sales+Opportunities/accounts.csv`
- `data/CRM+Sales+Opportunities/products.csv`
- `data/CRM+Sales+Opportunities/sales_teams.csv`

The app builds a semantic view called `opportunities_enriched` from these files and uses the dataset's latest close date as the analysis reference point.

Key derived fields include:

- `pipeline_velocity_days`
- `deal_age_days`
- `stage_age_days`
- `deal_age_bucket`
- `segment`
- `plan_tier`

## Sample Questions

- Why did pipeline velocity drop this week?
- Compare SMB vs Enterprise performance
- Which segment is underperforming?
- What should we do about this drop?
- Which deals should we prioritize?

## Running Tests

```bash
pytest
```

The test suite covers:

- mocked Gemini planner/synthesis contracts
- execution and verification behavior
- API response shape

## Docker

To launch both services together:

```bash
docker compose up --build
```

Then open:

- API: [http://localhost:8000](http://localhost:8000)
- UI: [http://localhost:8501](http://localhost:8501)

## Demo Script

1. Open the Streamlit UI.
2. Select "Why did pipeline velocity drop this week?"
3. Run the analysis and show the planner-executor loop spinner.
4. Open the executed-steps panel and show the generated SQL or pandas code.
5. Show the output preview for the most important step.
6. Highlight the verified badge and top-line change.
7. Expand the trace panel to show replanning-capable agent behavior.
8. Close on the tactical recommendation.

## Screenshots

Add screenshots here for:

- main dashboard
- evidence panel
- trace panel

## Known Limitations

- The current build is scoped to pipeline analytics on the provided CRM dataset.
- Churn analysis is out of scope until a real subscriptions or churn dataset is added.
- The planner is only allowed to use curated dataset views and bounded execution tools.
- Gemini is required for planning and final answer generation.

## Future Roadmap

- Add subscription and churn datasets for a second metric family
- Richer time window parsing
- Stronger execution-time linting for generated pandas steps
- LangSmith or Phoenix integration for trace export
- Stronger deal-prioritization playbooks
