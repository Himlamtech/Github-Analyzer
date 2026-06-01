# Integration

## Current state

The frontend now calls the backend directly for the core dashboard path.

## Frontend request map

- `/pipeline/status`: pipeline readiness and freshness badge
- `/events/latest`: recent activity sample in overview and runtime ticker
- `/dashboard/top-repos`: breakout table baseline
- `/dashboard/trending`: highlighted breakout repo and top mover context
- `/intelligence/rotation`: ecosystem rotation cards
- `/intelligence/news-impact`: curated backend snapshot for news-to-code analysis
- `/intelligence/news-impact/readiness`: operational readiness for external news-source ingestion
- `/intelligence/news-impact/sources/preview`: latest items fetched from enabled official RSS/Atom feeds
- `/intelligence/framework-radar`: curated backend snapshot for framework radar
- `/intelligence/weekly-brief/latest`: curated backend snapshot for weekly brief
- `/dashboard/repo-timeseries`: breakout detail drawer

## Current page contract map

| Frontend page | Current contract | Status |
|---|---|---|
| `Overview` | `/pipeline/status`, `/events/latest`, `/dashboard/top-repos`, `/dashboard/trending` | Live |
| `BreakoutDetector` | `/intelligence/breakout`, `/dashboard/repo-timeseries` | Live |
| `EcosystemRotation` | `/intelligence/rotation` plus curated visual framing | Partial |
| `NewsImpact` | `/intelligence/news-impact` | Partial |
| `CompetitiveRadar` | `/intelligence/framework-radar` | Partial |
| `WeeklyBrief` | `/intelligence/weekly-brief/latest` | Partial |

## Env contract

- frontend reads `VITE_API_BASE_URL`
- backend serves on `http://localhost:8000` by default

## Known gaps

- `NewsImpact`, `CompetitiveRadar`, and `WeeklyBrief` are served by curated backend snapshots, not external-source intelligence marts yet
- `NewsImpact` readiness for external ingestion is exposed separately so the team can verify mode, enabled sources, and missing prerequisites
- official external feed preview is available so the team can validate source wiring before building persistence and causality scoring
- some metrics shown in the UI are derived presentation metrics computed client-side from backend responses
- local frontend build requires Node.js 20+ because of the current Vite/Tailwind dependency line

## Integration principles

- The frontend should never query raw event storage directly.
- New intelligence pages should bind to curated marts or dedicated use-case endpoints.
- If a page needs confidence, durability, or false-hype metrics, those metrics must be computed server-side from a named model rather than improvised in the browser.
