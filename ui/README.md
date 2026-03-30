# Planera UI

Planera is a premium analytics copilot frontend built with React, TypeScript, Vite, Tailwind CSS, and React Router.

This app is designed to work against a separately hosted backend API and includes a dedicated service layer for:

- chat submission
- file uploads
- inspection data
- validation and trace metadata
- conversation history

When the backend is unavailable, the UI can fall back to seeded demo data so the product remains demo-ready.

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

4. Start the backend API separately on port `8000`

The current live integration expects the FastAPI backend from [`/Users/ayushgaur/MLH_UV/gtm-copilot`](/Users/ayushgaur/MLH_UV/gtm-copilot) to be running at `http://localhost:8000`.

4. Build for production

```bash
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
- `demo`: use demo data only
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

- [`src/api/client.ts`](./src/api/client.ts)
- [`src/api/chat.ts`](./src/api/chat.ts)
- [`src/api/uploads.ts`](./src/api/uploads.ts)
- [`src/api/inspections.ts`](./src/api/inspections.ts)

Current live contract:

- `POST /analyze` is used for real chat submissions
- `GET /sample-questions` can be added to the UI later for dynamic prompt suggestions
- live inspection data is derived from the `/analyze` response and cached client-side for the inspection drawer

Current gaps in the backend contract:

- uploads still fall back to demo behavior unless a real `/uploads` endpoint is added
- conversation history is currently local/demo until a backend history endpoint is introduced

If you want the frontend to use only real backend data, set:

```env
VITE_API_FALLBACK_MODE=live
```
