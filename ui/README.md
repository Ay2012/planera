# Planera UI

Planera is a premium analytics copilot frontend built with React, TypeScript, Vite, Tailwind CSS, and React Router.

This app is designed to work against a separately hosted backend API and includes a dedicated service layer for:

- authentication (JWT session against `POST /auth/login`, `POST /auth/signup`, `GET /auth/me`)
- **chat submission** via **`POST /chat`** (authenticated product path — the UI does not call `POST /analyze` for normal usage)
- file uploads
- inspection data
- validation and trace metadata
- conversation history (still mostly local/demo until a history API exists)

When the backend is unavailable, the UI can fall back to seeded demo data so the product remains demo-ready.

### Primary vs debug API (backend)

| Backend path | Used by this UI for normal signed-in flows? |
|--------------|---------------------------------------------|
| **`POST /chat`** | **Yes** — every real analysis turn goes here (`src/api/chat.ts`). |
| **`POST /analyze`** | **No** — stateless debug endpoint on the server only (Swagger/curl/Postman). Same analysis shape may appear embedded in `/chat` responses or mapped in TypeScript as `AnalyzeApiResponse` — that is a **payload type name**, not an HTTP call to `/analyze`. |

## Getting Started

1. Install dependencies

```bash
npm install
```

2. Configure environment variables

```bash
cp .env.example .env
```

3. Start the development server

```bash
npm run dev
```

4. Start the backend API from the repo root (`../` from this folder) on port `8000` (see root `README.md`: `source .venv/bin/activate` then `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`).

5. Build for production

```bash
npm run build
```

## Quality Checks

```bash
npm run lint
npm run test:run
npm run build
```

## Environment

Required:

```env
VITE_API_BASE_URL=http://localhost:8000
```

Optional:

```env
VITE_API_FALLBACK_MODE=hybrid
```

Fallback modes:

- `hybrid`: try the backend first, then fall back to seeded demo data
- `demo`: use demo data only for **analysis/upload** calls; **auth** (`/auth/*`) still hits the API so you can sign in while the rest of the app uses mocks
- `live`: fail loudly when the backend is unavailable

## Project Structure

```text
planera-ui/
├── public/
├── src/
│   ├── api/
│   ├── components/
│   │   ├── app/
│   │   ├── marketing/
│   │   └── shared/
│   ├── config/
│   ├── context/
│   ├── data/
│   ├── hooks/
│   ├── layouts/
│   ├── lib/
│   ├── pages/
│   ├── router/
│   ├── store/
│   ├── styles/
│   ├── types/
│   ├── App.tsx
│   └── main.tsx
├── .env
├── .env.example
├── package.json
├── tailwind.config.ts
├── tsconfig.json
├── tsconfig.node.json
└── vite.config.ts
```

## Backend Integration Notes

The frontend keeps request logic out of presentational components. Update endpoints in the service layer:

- [`src/api/client.ts`](./src/api/client.ts) — shared `request()` / `requestWithAuth()`; supports `authToken` and FastAPI validation (`422`) error text
- [`src/api/auth.ts`](./src/api/auth.ts) — login, signup, `/auth/me`
- [`src/api/chat.ts`](./src/api/chat.ts)
- [`src/api/uploads.ts`](./src/api/uploads.ts)
- [`src/api/inspections.ts`](./src/api/inspections.ts)

### Auth session

- [`src/context/AuthProvider.tsx`](./src/context/AuthProvider.tsx) and [`src/hooks/useAuth.ts`](./src/hooks/useAuth.ts) hold the current user and JWT; the token is stored under `planera.accessToken` in `localStorage`.
- [`src/router/ProtectedRoute.tsx`](./src/router/ProtectedRoute.tsx) guards `/app` and `/settings`; unauthenticated users go to `/sign-in` (with `state.from` for post-login redirect).
- Sign out clears storage and is available from the workspace sidebar and Settings.

Current live contract:

- `POST /auth/signup`, `POST /auth/login`, `GET /auth/me` — session and route protection
- `POST /chat` — real analysis turns (persisted conversations and assistant messages)
- `GET /conversations`, `GET /conversations/:id` — conversation list and thread hydration
- `POST /uploads` profiles CSV and TSV workspace uploads
- `GET /inspections/:id` fetches a stored inspection payload when it is not already cached client-side (requires auth when the snapshot came from `/chat`)
- `GET /sample-questions` can be wired for dynamic prompt suggestions

The backend still exposes **`POST /analyze`** for stateless debugging only; the **React app does not use it** for authenticated workspace usage.

If you want the frontend to use only real backend data, set:

```env
VITE_API_FALLBACK_MODE=live
```
