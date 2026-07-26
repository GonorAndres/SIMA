# SIMA Frontend

React 19 + TypeScript interface for SIMA, the Sistema Integral de Modelación
Actuarial. It provides mortality, pricing, reserve, sensitivity, and solvency
views in Spanish and English.

## Requirements

- Node.js 18 or newer
- The SIMA FastAPI backend running on `http://localhost:8000`

## Local development

From the repository root:

```bash
cd frontend
npm ci
npm run dev
```

Open `http://localhost:5173`. Vite proxies `/api` requests to
`http://localhost:8000`, as configured in `vite.config.ts`.

Start the backend in another terminal:

```bash
uvicorn backend.api.main:app --host 0.0.0.0 --port 8000
```

## Quality checks

```bash
npm run lint
npm run build
```

`npm run build` runs TypeScript project compilation before producing the
production bundle in `frontend/dist/`.

## Structure

- `src/pages/`: the six routed application pages.
- `src/components/`: charts, forms, shared layout, and data presentation.
- `src/api/client.ts`: API client and request handling.
- `src/types/`: TypeScript representations of API responses.
- `src/i18n.ts`: Spanish/English translations.
- `src/context/`: guided-demo state.
- `public/docs/` and `public/formulas/`: downloadable references and formula images.

The production Docker image serves `frontend/dist/` through FastAPI. The
frontend does not persist portfolio state; the backend currently holds one
shared in-memory demo portfolio that resets when the server restarts.
