# Integration

## Current state

The frontend now calls the backend directly for the core dashboard path.

## Frontend request map

- `/pipeline/status`: pipeline readiness and freshness badge
- `/events/latest`: recent activity sample in overview and runtime ticker
- `/dashboard/top-repos`: breakout table baseline
- `/dashboard/trending`: highlighted breakout repo and top mover context
- `/intelligence/rotation`: ecosystem rotation cards
- `/intelligence/news-impact`: computed backend news-to-code analysis from persisted official sources
- `/intelligence/news-impact/{event_id}`: detailed dossier for one computed news-impact event
- `/intelligence/news-impact/readiness`: operational readiness for external news-source ingestion
- `/intelligence/news-impact/sources/preview`: latest items fetched from enabled official RSS/Atom feeds
- `POST /intelligence/news-impact/sources/sync`: fetch enabled official sources and persist latest items into ClickHouse
- `/intelligence/news-impact/sources/latest`: latest persisted official external news items
- `/intelligence/news-impact/sources/health`: latest persisted source health snapshot per official source
- `/intelligence/framework-radar`: computed backend framework radar
- `/intelligence/weekly-brief/latest`: latest versioned weekly brief snapshot
- `/intelligence/weekly-brief/archive`: weekly brief archive metadata
- `/dashboard/repo-timeseries`: breakout detail drawer

## Current page contract map

| Frontend page | Current contract | Status |
|---|---|---|
| `Overview` | `/pipeline/status`, `/events/latest`, `/dashboard/top-repos`, `/dashboard/trending` | Live |
| `BreakoutDetector` | `/intelligence/breakout`, `/dashboard/repo-timeseries` | Live |
| `EcosystemRotation` | `/intelligence/rotation` | Live |
| `NewsImpact` | `/intelligence/news-impact` | Partial |
| `CompetitiveRadar` | `/intelligence/framework-radar` | Live |
| `WeeklyBrief` | `/intelligence/weekly-brief/latest` | Partial |

## Env contract

- frontend reads `VITE_API_BASE_URL`
- backend serves on `http://localhost:8000` by default

## Known gaps

- `NewsImpact` now serves computed responses from persisted official-source items, but the frontend may still need additional dossier UI to expose every backend field
- `NewsImpact` readiness for external ingestion remains exposed separately so the team can verify mode, enabled sources, and missing prerequisites
- official external feed preview is available so the team can validate source wiring before sync and persistence
- official external source sync now supports `fetch -> enrich -> quarantine -> persist -> read` for NewsImpact feed items and source health
- some metrics shown in the UI are derived presentation metrics computed client-side from backend responses
- local frontend build requires Node.js 20+ because of the current Vite/Tailwind dependency line

## Integration principles

- The frontend should never query raw event storage directly.
- New intelligence pages should bind to curated marts or dedicated use-case endpoints.
- If a page needs confidence, durability, or false-hype metrics, those metrics must be computed server-side from a named model rather than improvised in the browser.
