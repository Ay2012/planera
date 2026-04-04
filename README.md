# GTM Analytics Copilot

GTM Analytics Copilot is an agentic analytics MVP for GTM teams. It takes a business question like "Why did pipeline velocity drop this week?", loads schema context for the dataset, uses an LLM to plan the next SQL or pandas step, executes it over curated views, replans on failure, then runs a single analysis pass to produce a markdown narrative. The API returns that analysis plus trace and executed steps.

## Why This Is Not "Chat With CSV"

This project is intentionally constrained:

- It uses an LLM planner, but only over curated dataset views.
- It does not let the model access arbitrary files or external systems.
- It executes exact SQL or restricted pandas steps instead of vague chain-of-thought.
- It replans using execution errors instead of silently falling back to rules.
- It does not run a separate deterministic verification layer; the narrative is grounded in executed step outputs.
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
- OpenAI or Gemini for planning and final analysis text (see `LLM_PROVIDER`)

Workflow:

1. Load curated views and a schema-only manifest (tables, columns, dtypes, row counts)
2. Ask the LLM for the next executable step (or finish)
3. Execute SQL (DuckDB) or restricted pandas
4. On failure or empty results, review and replan
5. Loop until the planner finishes or limits are hit
6. Ask the LLM once to turn the executed results into markdown analysis
7. Return `analysis`, `trace`, `executed_steps`, and `errors`

Core modules:

- `app/data/semantic_model.py`: curated dataset views and schema manifest
- `app/llm/`: OpenAI or Gemini client
- `app/agent/planner.py`: compiled multi-step SQL plan and optional repair
- `app/agent/executor.py`: SQL execution engine (pandas helpers retained)
- `app/agent/analysis.py`: single-pass narrative from query + steps
- `app/agent/graph.py`: LangGraph orchestration
- `app/api/routes.py`: Shared API surface (health, uploads, inspections, **stateless** `POST /analyze`)
- `app/api/chat_routes.py`: **Primary product** chat API (`POST /chat`, conversation history)
- `ui/`: React + Vite frontend

### API: primary chat vs stateless analyze

| Path | Role |
|------|------|
| **`POST /chat`** (with JWT) | **Product path:** persists conversations, messages, and inspection snapshots; use for the React app and any integrated client. |
| **`POST /analyze`** (no auth) | **Debug / manual testing:** same analytics engine, but **no persistence** and inspection data only in server memory until restart. Marked **deprecated** in OpenAPI; do not treat it as a peer to `/chat`. |

## Repo Structure

```text
planera/
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
cd planera
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Use this project virtualenv for all Python commands (`uvicorn`, `pytest`, `pip`). In each new shell, activate it first:

```bash
source .venv/bin/activate
```

*(Windows Git Bash: `source .venv/Scripts/activate` — PowerShell: `.venv\Scripts\Activate.ps1`.)*

### 2. Run the API

```bash
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API endpoints:

- `GET /health`
- `GET /sample-questions`
- `POST /uploads`
- `GET /inspections/{inspection_id}`
- **`POST /chat`** — **primary:** authenticated analysis turn; persists thread + inspection snapshot
- `GET /conversations`, `GET /conversations/{id}` — list/load chat history (authenticated)
- `POST /analyze` — **deprecated / debug only:** stateless run (see table above)
- `POST /auth/signup` — create user (SQLite), returns JWT
- `POST /auth/login` — issue JWT
- `GET /auth/me` — current user (`Authorization: Bearer <token>`)

**Database:** On API startup the app creates SQLite tables if needed (no separate migration step for this demo). By default the DB file is `planera.db` in the project root (same directory as `requirements.txt`). Override with `DATABASE_PATH` in `.env`. Add a strong `JWT_SECRET_KEY` before any shared deployment; the repo default is for local dev only.

Example (debug — stateless; prefer `/chat` with a JWT for real usage):

```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"query":"Why did pipeline velocity drop this week?"}'
```

### 3. Run the React UI

In a second terminal:

```bash
cd ui
nodeenv -p --prebuilt    
npm install
npm run dev
```

## Environment Variables

Backend settings are defined in `.env.example`:

- `APP_NAME`
- `APP_ENV`
- `API_HOST`
- `API_PORT`
- `GEMINI_API_KEY`
- `GEMINI_MODEL`
- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `LOG_LEVEL`
- `DATABASE_PATH` (optional; default `planera.db` beside `requirements.txt`)
- `JWT_SECRET_KEY` (optional for local dev; **required** for non-local use)
- `JWT_ALGORITHM` (default `HS256`)
- `ACCESS_TOKEN_EXPIRE_MINUTES` (default `10080`)

Frontend settings live in `ui/.env.example`.

Set `LLM_PROVIDER` to `openai` or `gemini` and provide the matching API key (`OPENAI_API_KEY` or `GEMINI_API_KEY`).

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

Use the project virtualenv so `pytest` and packages like `passlib` match `requirements.txt` (if you use Conda/base Python, a bare `pytest` may run the wrong interpreter and fail imports):

```bash
source .venv/bin/activate
pip install -r requirements.txt
python -m pytest
```

The test suite covers:

- mocked LLM planner and analysis contracts
- executor and review behavior
- API response shape

## Docker

To launch both services together:

```bash
docker compose up --build
```

Then open:

- API: [http://localhost:8000](http://localhost:8000)
- UI: [http://localhost:5173](http://localhost:5173)

## Demo Script

1. Open the Planera UI.
2. Select "Why did pipeline velocity drop this week?"
3. Run the analysis and show the planner-executor loop spinner.
4. Open the executed-steps panel and show the generated SQL or pandas code.
5. Show the output preview for the most important step.
6. Expand the trace panel to show replanning-capable agent behavior.
7. Close on the markdown analysis and next best insights.

## Screenshots

Add screenshots here for:

- main dashboard
- analysis panel
- trace panel

## Known Limitations

- The current build is scoped to pipeline analytics on the provided CRM dataset.
- Churn analysis is out of scope until a real subscriptions or churn dataset is added.
- The planner only sees registered views; execution is SQL or restricted pandas.
- An API key is required for the configured `LLM_PROVIDER` (OpenAI or Gemini).

## Future Roadmap

- Add subscription and churn datasets for a second metric family
- Richer time window parsing
- Stronger execution-time linting for generated pandas steps
- LangSmith or Phoenix integration for trace export
- Stronger deal-prioritization playbooks
