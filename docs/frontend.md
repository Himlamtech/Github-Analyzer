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

### Curated presentation views

- `EcosystemRotation`
- `NewsImpact`
- `WeeklyBrief`
- `CompetitiveRadar`

These views remain useful for storytelling and design presentation, but they are not all at the same maturity level anymore.

Current maturity split:

- `EcosystemRotation`: partial backend binding
- `NewsImpact`: backend snapshot + external-source preview/sync foundation
- `CompetitiveRadar`: backend snapshot
- `WeeklyBrief`: backend snapshot

## Binding rule

The frontend should follow this rule strictly:

- if a panel represents current system state, it must read live backend data
- if a panel is exploratory or editorial, it may remain curated until a backend contract exists

This keeps the UI honest while still allowing the new visual direction to move ahead of future data products.

## Current live page mapping

- `Overview`: pipeline status, latest events, top movers
- `BreakoutDetector`: top repos and repo time series
- `EcosystemRotation`: category rotation contract from `/intelligence/rotation`
- `NewsImpact`: curated main narrative from `/intelligence/news-impact`; external source operations exist in backend but are not surfaced in the main UI yet
- `CompetitiveRadar`: backend snapshot from `/intelligence/framework-radar`
- `WeeklyBrief`: backend snapshot from `/intelligence/weekly-brief/latest`

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
