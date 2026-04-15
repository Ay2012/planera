# Planera

Planera is a chat-first analytics workspace for structured data. You sign in, upload CSV or JSON files, ask a business question, and review both the answer and the execution trail behind it.

The product is designed to feel closer to an analytics copilot than a generic "chat with files" tool:

- uploads are scoped to the signed-in user
- analysis runs through a bounded plan/query/execute loop
- answers come back with trace, SQL, result previews, and validation context
- conversation history and inspection snapshots are persisted for the main chat flow

## Current Workflow

1. Sign in from the UI
2. Upload one or more CSV or JSON files
3. Start a chat or continue an existing conversation
4. Ask a question against the attached uploads
5. Review the answer, then open the inspection panel for SQL, results, trace, and validation details

## Product Surface

Backend:

- FastAPI API
- SQLite for users, conversations, messages, and inspection snapshots
- DuckDB for uploaded data and query execution
- OpenAI or Gemini for the planning and answer-generation steps

Frontend:

- React + Vite workspace UI
- authenticated chat experience
- uploads management
- inspection drawer for execution details

## API Overview

Primary app flow:

- `POST /auth/signup`
- `POST /auth/login`
- `GET /auth/me`
- `GET /uploads`
- `POST /uploads`
- `DELETE /uploads/{source_id}`
- `POST /chat`
- `GET /conversations`
- `GET /conversations/{id}`
- `GET /inspections/{inspection_id}`

Debug-only helper:

- `POST /analyze`

Notes:

- `POST /chat` is the main product API and is what the React app uses for real analysis turns.
- `POST /analyze` is a deprecated debug path. It is stateless, still authenticated, and should not be treated as the normal integration path.

## Repo Structure

```text
planera/
├── app/          # FastAPI backend
├── ui/           # React frontend
├── data/         # sample data, uploads, and DuckDB registry files
├── tests/
├── requirements.txt
├── docker-compose.yml
├── Dockerfile
└── README.md
```

## Local Setup

### 1. Backend

```bash
cd planera
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Frontend

In a second terminal:

```bash
cd ui
npm install
npm run dev
```

Open:

- API: [http://localhost:8000](http://localhost:8000)
- UI: [http://localhost:5173](http://localhost:5173)

## Environment Variables

Start from `.env.example` for backend setup, then override additional runtime paths or secrets as needed.

Most important:

- `LLM_PROVIDER`
- `OPENAI_API_KEY` or `GEMINI_API_KEY`
- `OPENAI_MODEL` or `GEMINI_MODEL`
- `DATABASE_PATH`
- `JWT_SECRET_KEY`
- `UPLOAD_STORAGE_DIR`
- `REGISTRY_PATH`
- `CORS_ALLOW_ORIGINS`

Frontend settings live in `ui/.env.example`.

Most important:

- `VITE_API_BASE_URL`
- `VITE_API_FALLBACK_MODE`

## Running Tests

Backend:

```bash
source .venv/bin/activate
python -m pytest
```

Frontend:

```bash
cd ui
npm run check
```

## Docker

To run both services together:

```bash
docker compose up --build
```

## Notes

- The current product flow is upload-first: the UI expects attached CSV or JSON files before submitting an analysis turn.
- The repository still contains sample CRM-style data under `data/`, but the active app flow is centered on user uploads rather than a built-in warehouse connection.
- Uploaded sources are scoped correctly, but separate uploads are not automatically joined just because they share similarly named columns.
- A valid API key is required for whichever LLM provider is configured.
