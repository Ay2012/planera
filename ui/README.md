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

4. Start the backend API from this repo separately on port `8000`

The current live integration expects the FastAPI backend in [`/Users/ayushgaur/MLH_UV/planera`](/Users/ayushgaur/MLH_UV/planera) to be running at `http://localhost:8000`.

4. Build for production

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
- `POST /uploads` profiles CSV and TSV workspace uploads
- `GET /inspections/:id` fetches a stored inspection payload when it is not already cached client-side
- `GET /sample-questions` can be added to the UI later for dynamic prompt suggestions

Current gaps in the backend contract:

- conversation history is currently local/demo until a backend history endpoint is introduced

If you want the frontend to use only real backend data, set:

```env
VITE_API_FALLBACK_MODE=live
```
