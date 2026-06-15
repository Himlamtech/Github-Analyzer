# Backend

## Layers

- `domain`: pure business objects and exceptions
- `application`: orchestration use cases and response DTOs
- `infrastructure`: GitHub, Kafka, Spark, ClickHouse, Parquet, config, logging
- `presentation`: FastAPI routes only

## Runtime flow

1. `PollGithubEventsUseCase` polls GitHub and publishes filtered events to Kafka.
2. `ProcessEventStreamUseCase` runs Spark streaming from Kafka to ClickHouse and Parquet.
3. FastAPI exposes health and dashboard analytics from ClickHouse-backed services.

## Serving model

- `ClickHouse` is the online serving source of truth.
- `Parquet` is the archive and backfill source, not a frontend-serving path.
- FastAPI should serve stable analytics and intelligence reads rather than exposing raw-storage complexity to the frontend.

## Current API surface used by the frontend

- `GET /health`
- `GET /pipeline/status`
- `GET /events/latest`
- `GET /dashboard/top-repos`
- `GET /dashboard/trending`
- `GET /dashboard/repo-timeseries`
- `GET /intelligence/breakout`
- `GET /intelligence/rotation`
- `GET /intelligence/news-impact`
- `GET /intelligence/news-impact/{event_id}`
- `GET /intelligence/news-impact/readiness`
- `GET /intelligence/news-impact/sources/preview`
- `POST /intelligence/news-impact/sources/sync`
- `GET /intelligence/news-impact/sources/latest`
- `GET /intelligence/news-impact/sources/health`
- `GET /intelligence/framework-radar`

## Current backend constraints

- Core repository category logic is still simplified in the ingestion path, but intelligence routes now map raw topics into product-facing taxonomy labels.
- `NewsImpact` now computes serving payloads from persisted official-source items, with duplicate and low-confidence quarantine flags stored at ingestion time.
- `FrameworkRadar` now computes framework metrics from live repository analytics inputs instead of a fixed snapshot.
- CORS now allows both `localhost:3000` and `localhost:5173` dev origins.

## Target backend direction

When the intelligence product expands, backend work should be organized into three groups of use case:

1. Intelligence use cases
2. Stability and guardrail use cases
3. External data control use cases

Examples of the next meaningful backend additions:

- entity linking for persisted external news items
- duplicate and low-confidence quarantine for external source content
- causality scoring between external launch/news items and GitHub telemetry
- deeper entity-linking between external news items and repo/framework registries
- richer framework/category marts replacing heuristic matching in the current phase

## Guardrails

- Do not add a dashboard endpoint unless there is a credible analytical model behind it.
- Do not push business scoring logic into the presentation layer.
- Prefer splitting large analytical services by use case when complexity grows, instead of turning one query service into a product monolith.
