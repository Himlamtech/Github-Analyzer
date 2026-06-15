# Frontend

## Stack

- React 19
- Vite 6
- Tailwind CSS 4
- Recharts
- Motion

## Current frontend model

The frontend is intentionally split into two groups:

### Live views

- `Overview`
- `BreakoutDetector`
- top runtime banner and pipeline notice

These views fetch backend data through `frontend/src/lib/api.ts` and hooks under `frontend/src/hooks/`.

### Intelligence views

- `EcosystemRotation`
- `NewsImpact`
- `CompetitiveRadar`

These views now read backend intelligence contracts, but they are not all at the same maturity level yet.

Current maturity split:

- `EcosystemRotation`: live backend rotation intelligence with taxonomy-aware categories
- `NewsImpact`: computed backend intelligence + external-source operations
- `CompetitiveRadar`: computed backend framework radar

## Binding rule

The frontend should follow this rule strictly:

- if a panel represents current system state, it must read live backend data
- if a panel is exploratory or editorial, it should still surface that status clearly even when backed by a lightweight backend contract

This keeps the UI honest while still allowing the new visual direction to move ahead of future data products.

## Current live page mapping

- `Overview`: pipeline status, latest events, top movers
- `BreakoutDetector`: top repos and repo time series
- `EcosystemRotation`: category rotation contract from `/intelligence/rotation`
- `NewsImpact`: computed news-to-code analysis from `/intelligence/news-impact` plus detail drill-down from `/intelligence/news-impact/{event_id}`
- `CompetitiveRadar`: computed framework radar from `/intelligence/framework-radar`

## Runtime configuration

- `VITE_API_BASE_URL`: FastAPI base URL

## Development commands

```bash
cd frontend
npm install
npm run dev
npm run type-check
npm run build
```
