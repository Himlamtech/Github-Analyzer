# Technique

## Backend tooling

- Python 3.14 via `uv`
- Ruff
- Mypy strict mode
- Pytest
- FastAPI
- structlog

## Data tooling

- Kafka
- Spark Structured Streaming
- ClickHouse
- Parquet

## Frontend tooling

- Vite
- React
- Tailwind CSS
- Recharts

## Runtime and performance notes

- Local frontend build should be treated as Node.js `20+` work.
- Backend serving should avoid full raw-table scans on request paths once intelligence pages expand.
- Expensive scoring and aggregation belongs in scheduled builds or curated marts, not in ad-hoc frontend-triggered queries.

## Working conventions

- keep architecture boundaries strict
- prefer minimal complete diffs
- use DTOs for API contracts
- treat docs as implementation artifacts, not marketing copy
