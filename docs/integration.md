# Integration

## Current state

The frontend now calls the backend directly for the core dashboard path.

## Frontend request map

- `/pipeline/status`: pipeline readiness and freshness badge
- `/events/latest`: recent activity sample in overview and runtime ticker
- `/dashboard/top-repos`: breakout table baseline
- `/dashboard/trending`: highlighted breakout repo and top mover context
- `/dashboard/topic-rotation`: ecosystem rotation cards
- `/dashboard/repo-timeseries`: breakout detail drawer

## Current page contract map

| Frontend page | Current contract | Status |
|---|---|---|
| `Overview` | `/pipeline/status`, `/events/latest`, `/dashboard/top-repos`, `/dashboard/trending` | Live |
| `BreakoutDetector` | `/dashboard/top-repos`, `/dashboard/repo-timeseries` | Live |
| `EcosystemRotation` | `/dashboard/topic-rotation` plus curated visual framing | Partial |
| `NewsImpact` | no backend contract yet | Curated |
| `CompetitiveRadar` | no backend contract yet | Curated |
| `WeeklyBrief` | no backend contract yet | Curated |

## Env contract

- frontend reads `VITE_API_BASE_URL`
- backend serves on `http://localhost:8000` by default

## Known gaps

- curated views do not yet have dedicated backend contracts
- some metrics shown in the UI are derived presentation metrics computed client-side from backend responses
- local frontend build requires Node.js 20+ because of the current Vite/Tailwind dependency line

## Integration principles

- The frontend should never query raw event storage directly.
- New intelligence pages should bind to curated marts or dedicated use-case endpoints.
- If a page needs confidence, durability, or false-hype metrics, those metrics must be computed server-side from a named model rather than improvised in the browser.
