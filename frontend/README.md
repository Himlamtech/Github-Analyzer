# Frontend

This directory now contains the primary dashboard frontend for the project.

## Stack

- React 19
- Vite 6
- Tailwind CSS 4
- Recharts

## Environment

Copy `.env.example` to `.env` when you want to override the backend URL.

```bash
cp .env.example .env
```

Available variables:

- `VITE_API_BASE_URL`: FastAPI base URL, default `http://localhost:8000`
- `VITE_ALLOWED_HOSTS`: Comma-separated extra hosts allowed by the Vite dev server, default includes `github.chipthoc.com`

## Commands

```bash
npm install
npm run dev
npm run build
npm run type-check
```

## Live integrations

The frontend consumes these backend endpoints directly:

- `GET /pipeline/status`
- `GET /events/latest`
- `GET /dashboard/top-repos`
- `GET /dashboard/trending`
- `GET /dashboard/topic-rotation`
- `GET /dashboard/repo-timeseries`

The `News Impact`, `Weekly Brief`, and `Competitive Radar` views currently remain curated presentation views. The `Overview`, `Breakout Detector`, and top-bar runtime status use live backend data.
