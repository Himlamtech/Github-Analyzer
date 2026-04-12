# GitHub AI Trend Analyzer — Copilot Instructions

## Architecture Overview

Real-time ingestion pipeline: **GitHub Events API → Kafka → Spark Structured Streaming → Parquet + ClickHouse → FastAPI/DuckDB**.

Strict **Clean Architecture + DDD** with inward-only dependencies:

```
Presentation → Application → Domain ← Infrastructure
```

| Layer                 | Entry Point                                            | Key Rule                                                             |
| --------------------- | ------------------------------------------------------ | -------------------------------------------------------------------- |
| `src/domain/`         | `entities/`, `value_objects/`, `repositories/`         | Zero external imports. All exceptions defined here.                  |
| `src/application/`    | `use_cases/`, `dtos/`                                  | Imports Domain only. No business logic — delegates to Domain.        |
| `src/infrastructure/` | `github/`, `kafka/`, `spark/`, `storage/`, `config.py` | Implements Domain ABCs. Wraps all external I/O.                      |
| `src/presentation/`   | `api/routes.py`                                        | FastAPI only. Calls Application DTOs, never Infrastructure directly. |

## Critical Data Flow

1. `PollGithubEventsUseCase` (`make stream`) — async loop polls GitHub API via `AsyncGithubClient`, runs `AiEventFilter`, maps to `GithubEventOutputDTO`, publishes to Kafka topic `github_raw_events` (16 partitions).
2. `ProcessEventStreamUseCase` (`make process`) — launches `GithubStreamingJob`: single Kafka readStream → **dual sink** (Parquet append + ClickHouse `foreachBatch`), 60s micro-batches, 10min watermark.
3. FastAPI (`/events/*`) queries ClickHouse for latest rows; DuckDB reads Parquet via `read_parquet('data/raw/**/*.parquet', hive_partitioning=true)` for analytics.

## Key Patterns

### Use Case Structure

Each use case has **one public method** (`execute()`) and accepts dependencies via constructor using `Protocol` (not ABC) to avoid tight coupling to infrastructure:

```python
class KafkaProducerProtocol(Protocol):
    async def publish(self, event: GithubEventOutputDTO) -> None: ...

class PollGithubEventsUseCase:
    def __init__(self, client: GitHubClientProtocol, ...) -> None: ...
    async def execute(self) -> None: ...
```

### Domain Exceptions

All exceptions inherit from `DomainException` (in `src/domain/exceptions.py`). Raise specific subtypes — never bare `Exception` or `ValueError`:

```python
raise InvalidEventTypeError(f"Unknown type: {raw!r}")  # not ValueError
raise ClickHouseWriteError("Batch insert failed")
```

### Value Objects

`@dataclass(frozen=True)` for domain VOs; Pydantic `model_config = ConfigDict(frozen=True)` for DTOs:

- `EventType(str, Enum)` — inherits `str` so JSON serialization works without unwrapping
- `RepositoryId` — validated `owner/name` format via `from_api(repo_id, repo_name)`

### DTOs

`GithubEventInputDTO` = raw API → use case boundary. `GithubEventOutputDTO` = domain entity → Kafka/API wire format. Field names in `GithubEventOutputDTO` **must match** the Spark `StructType` in `src/infrastructure/spark/schemas.py`.

### Infrastructure Clients

- **ClickHouse**: uses `clickhouse-driver` on **port 9000** (native TCP). `asyncio.to_thread` wraps sync driver calls. JDBC/HTTP port 8123 is only for external tooling.
- **Kafka**: `aiokafka` async producer/consumer. Event payloads serialized with `orjson`.
- **Spark**: session constructed in `src/infrastructure/spark/session_factory.py`. Schema is explicit `StructType` from `schemas.py` — never infer schema from JSON.

### Logging

Use `structlog` exclusively. Never use `logging` directly:

```python
logger = structlog.get_logger(__name__)
logger.info("event_published", event_id=event.event_id, repo=event.repo_name)
```

### Metrics

Prometheus counters/gauges live in `src/infrastructure/observability/metrics.py`. Increment at the infrastructure boundary, not in domain or use cases.

## Developer Workflows

```bash
make setup       # Start Docker stack (Kafka, ClickHouse, Prometheus, Grafana) + init tables
make stream      # Run GitHub poller (python -m src.application.use_cases.poll_github_events)
make process     # Run Spark streaming job
make test        # pytest --cov=src (≥80% coverage required)
make lint        # ruff check + ruff format --check + mypy --strict
make format      # ruff format + ruff check --fix (auto-fix)
make clean       # docker-compose down -v + rm data/
```

Config is loaded from `.env` via `pydantic-settings`. Copy `.env.example` and set `GITHUB_API_TOKENS` and `CLICKHOUSE_PASSWORD` before running.

## Testing Conventions

- Mirror source tree: `src/domain/entities/github_event.py` → `tests/domain/test_github_event.py`
- **Mock only at infrastructure boundary** — repositories, HTTP clients, Kafka. Never mock domain internals.
- Shared fixtures in `tests/conftest.py`: `sample_github_event`, `sample_repo_id`, `raw_watch_event`, `utc_now`.
- All `created_at` datetimes must be **timezone-aware UTC** — bare `datetime.now()` will raise `ValidationError` in `GithubEvent.__post_init__`.
- Naming: `test_<method>_<scenario>_<expected_result>` (e.g. `test_create_user_duplicate_email_raises_conflict`).

## Project-Specific Gotchas

- **Parquet partitioning** uses Hive-style columns `event_date=YYYY-MM-DD/event_type=XxxEvent/`. These are derived from `GithubEvent.event_date()` and `EventType.value`, not stored as data columns.
- **AI relevance filter** (`src/infrastructure/github/event_filter.py`) runs before Kafka publish. Criteria: topic match OR description keyword match OR repo-name pattern match — AND NOT (bot actor OR spam signal). Adding new AI frameworks means updating `_AI_TOPICS`, `_AI_KEYWORDS`, or `_AI_REPO_NAME_PATTERNS`.
- **Token rotation**: `PollGithubEventsUseCase` supports comma-separated `GITHUB_API_TOKENS`. All exhausted → `RateLimitExceededError` → sleep until earliest reset.
- **ETag caching**: GitHub client sends `If-None-Match` header. HTTP 304 → skip batch, no Kafka publish.
- Python **3.11**, line length **99**, `from __future__ import annotations` at top of every file.
