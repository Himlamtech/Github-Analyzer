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
- FastAPI should serve curated analytics reads rather than exposing raw-storage complexity to the frontend.

## Current API surface used by the frontend

- `GET /health`
- `GET /pipeline/status`
- `GET /events/latest`
- `GET /dashboard/top-repos`
- `GET /dashboard/trending`
- `GET /dashboard/topic-rotation`
- `GET /dashboard/repo-timeseries`

## Current backend constraints

- Dashboard category logic is currently simplified and mostly falls back to neutral classification.
- Some presentation views in the frontend do not yet have dedicated backend endpoints.
- CORS now allows both `localhost:3000` and `localhost:5173` dev origins.

## Target backend direction

When the intelligence product expands, backend work should be organized into three groups of use case:

1. Intelligence use cases
2. Stability and guardrail use cases
3. External data control use cases

Examples of the next meaningful backend additions:

- breakout confidence and explanation traces
- ecosystem rotation built from curated category-level marts
- source freshness and serving-read protection
- external launch/news sync before `NewsImpact` becomes live

## Guardrails

- Do not add a dashboard endpoint unless there is a credible analytical model behind it.
- Do not push business scoring logic into the presentation layer.
- Prefer splitting large analytical services by use case when complexity grows, instead of turning one query service into a product monolith.
