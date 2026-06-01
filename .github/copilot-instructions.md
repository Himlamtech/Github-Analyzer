# GitHub AI Trend Analyzer — Copilot Instructions

## Architecture Overview

Real-time ingestion pipeline: **GitHub Events API -> Kafka -> Spark Structured Streaming -> Parquet + ClickHouse -> FastAPI**.

Strict **Clean Architecture + DDD** with inward-only dependencies:

```
Presentation -> Application -> Domain <- Infrastructure
```

| Layer | Entry Point | Key Rule |
| --- | --- | --- |
| `src/domain/` | `entities/`, `value_objects/`, `repositories/` | Zero external imports. All exceptions defined here. |
| `src/application/` | `use_cases/`, `dtos/` | Imports Domain only. No business logic in presentation. |
| `src/infrastructure/` | `github/`, `kafka/`, `spark/`, `storage/`, `config.py` | Implements ports and wraps external I/O. |
| `src/presentation/` | `api/routes.py` | FastAPI only. Calls application/use-case boundaries. |

## Critical Data Flow

1. `PollGithubEventsUseCase` (`make stream`) polls GitHub via `AsyncGithubClient`, filters events, maps DTOs, then publishes to Kafka topic `github_raw_events`.
2. `ProcessEventStreamUseCase` (`make process`) launches the Spark streaming job and writes to the dual sinks `Parquet + ClickHouse`.
3. FastAPI routes serve product and dashboard responses from ClickHouse-backed services. Parquet remains archive/backfill input, not a public serving path.

## Key Patterns

### Use Case Structure

Each use case exposes one public `execute()` entrypoint and receives dependencies by constructor.

### Domain Exceptions

All custom exceptions inherit from `DomainException` in `src/domain/exceptions.py`. Raise specific subtypes instead of generic exceptions.

### DTOs and Schemas

`GithubEventOutputDTO` field names must stay aligned with the Spark schema in `src/infrastructure/spark/schemas.py`.

### Infrastructure Clients

- **ClickHouse** uses `clickhouse-driver` on port `9000`.
- **Kafka** uses `aiokafka` and `orjson`.
- **Spark** uses explicit schemas from `schemas.py`.

### Logging

Use `structlog` only:

```python
logger = structlog.get_logger(__name__)
logger.info("event_published", event_id=event.event_id, repo=event.repo_name)
```

## Developer Workflows

```bash
make setup
make stream
make process
make test
make lint
make format
make clean
```

Config is loaded from `.env` via `pydantic-settings`. Use `uv sync` to install dependencies and run commands through `uv`.

## Testing Conventions

- Mirror the source tree under `tests/`.
- Mock at infrastructure boundaries, not inside domain logic.
- Keep datetimes timezone-aware UTC.
- Naming follows `test_<unit>_<scenario>_<expected_result>`.

## Project-Specific Gotchas

- Parquet partitioning uses Hive-style `event_date=YYYY-MM-DD/event_type=XxxEvent/`.
- The AI relevance filter runs before Kafka publish.
- Token rotation supports comma-separated `GITHUB_API_TOKENS`.
- GitHub API requests use ETag caching where available.
- Python version is `3.14`, line length is `99`, and modules should use `from __future__ import annotations`.
