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

These views remain useful for storytelling and design presentation, but they are not yet driven fully by backend APIs.

## Binding rule

The frontend should follow this rule strictly:

- if a panel represents current system state, it must read live backend data
- if a panel is exploratory or editorial, it may remain curated until a backend contract exists

This keeps the UI honest while still allowing the new visual direction to move ahead of future data products.

## Current live page mapping

- `Overview`: pipeline status, latest events, top movers
- `BreakoutDetector`: top repos and repo time series
- `EcosystemRotation`: currently mixed, prefers live topic rotation data when available

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
