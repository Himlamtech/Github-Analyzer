# GitHub AI Trend Analyzer

Real-time pipeline that tracks AI/ML activity on GitHub by ingesting events,
enriching repository metadata, and exposing a live analytics dashboard.

## Architecture

```
GitHub Events API
       │
       ▼
PollGithubEventsUseCase ── AiEventFilter ──▶ Kafka (github_raw_events, 16 partitions)
                                                      │
                                        ┌─────────────┘
                                        ▼
                             Spark Structured Streaming
                             (60s micro-batches, 10min watermark)
                                        │
                        ┌───────────────┴──────────────┐
                        ▼                               ▼
                  ClickHouse                     Parquet (Hive)
              (github_data table)          data/raw/event_date=.../
                        │
              ┌─────────┴──────────┐
              ▼                    ▼
          FastAPI        Ollama (bge-m3, llama3.2:3b)
         (port 8000)         SearXNG (external)
              │           search, grounded briefs, news radar
              ▼
        Next.js Dashboard
          (port 3000)
```

**Observability:** FastAPI `/metrics` → Prometheus (port 9093) → Grafana (port 3001)

## Services

| Service | Default host port | Purpose |
|---------|------|---------|
| Next.js frontend | `3000` | Live dashboard UI |
| FastAPI | `8000` | Dashboard API + pipeline endpoints |
| Kafka | `9092` | Event streaming (16 partitions) |
| ClickHouse HTTP | `8123` | External tooling / UI |
| ClickHouse native | `9100` | Host-mapped native TCP (`9000` inside Docker network) |
| Prometheus | `9093` | Metrics scraper |
| Grafana | `3001` | Metrics dashboard |
| Ollama | `11435` | Embeddings + grounded brief generation |

## Quickstart

### Prerequisites

- Docker + Docker Compose
- Conda environment `github` with Python 3.14
- Java 17+ (required for PySpark — included in the Docker image)

### 1. Configure environment

```bash
cp .env.example .env
# Set GITHUB_API_TOKENS and CLICKHOUSE_PASSWORD at minimum
conda activate github
pip install -e ".[dev]"
```

### 2. Start all infrastructure services

```bash
make setup
```

Starts Zookeeper, Kafka (16 partitions), ClickHouse, Prometheus, Grafana, Ollama, and the FastAPI + Next.js containers. Waits for health checks and initialises ClickHouse tables via `clickhouse/init.sql`.

To enable the AI endpoints, pull the Ollama models on demand after setup:

```bash
make ai-models
```

If a host port is already occupied by another local stack, override it before `docker compose up`, for example:

```bash
CLICKHOUSE_HTTP_PORT=18123 API_PORT=18000 docker compose up -d --build frontend
```

Supported host-port overrides:

```bash
FRONTEND_PORT
API_PORT
KAFKA_PORT
KAFKA_JMX_HOST_PORT
CLICKHOUSE_HTTP_PORT
CLICKHOUSE_NATIVE_PORT
PROMETHEUS_PORT
GRAFANA_PORT
OLLAMA_PORT
```

If you already have a local Parquet archive under `data/raw`, bootstrap ClickHouse before opening the dashboard:

```bash
make bootstrap-clickhouse
```

### 3. Run the live pipeline

```bash
make stream            # GitHub Events API → Kafka (foreground)
make process           # Spark: Kafka → ClickHouse + Parquet (foreground)
```

### 4. Enrich repo metadata

```bash
make sync-repos          # Load data/repos/*.json → repo_metadata table
make sync-events-repos   # Enrich repos found in active events from ClickHouse
make enrich-repos        # Bulk GitHub API enrichment for all known repos
```

### 5. Monitor

```bash
make monitor     # Opens Grafana at http://localhost:3001
```

Default credentials: `admin` / value of `GRAFANA_PASSWORD` (default: `admin`)

Dashboard: http://localhost:3000

---

## Project Structure

```
src/
├── domain/                       # Zero external dependencies
│   ├── exceptions.py             # DomainException hierarchy
│   ├── entities/                 # GithubEvent aggregate root, RepoMetadata
│   ├── value_objects/            # EventType (str Enum), RepositoryId, RepoCategory
│   ├── repositories/             # ABCs: EventRepository, RepoMetadataRepository
│   └── services/                 # CategoryClassifier
├── application/
│   ├── dtos/                     # Input / Output / Query DTOs
│   └── use_cases/
│       ├── poll_github_events.py        # GitHub API → Kafka
│       ├── process_event_stream.py      # Kafka → ClickHouse + Parquet (Spark)
│       └── sync_repo_metadata.py        # data/repos/*.json → ClickHouse
├── infrastructure/
│   ├── config.py                 # pydantic-settings Settings singleton
│   ├── github/                   # AsyncGithubClient, AiEventFilter, EventMapper
│   ├── kafka/                    # aiokafka producer/consumer/admin
│   ├── spark/                    # SparkSession factory, StreamingJob, Schemas
│   ├── storage/                  # ClickHouseRepository, ParquetRepository,
│   │                             #   ClickHouseDashboardService
│   └── observability/            # Prometheus metrics, structlog config
└── presentation/
    └── api/
        ├── routes.py             # /health /pipeline/status /events/*
        └── dashboard_routes.py   # /dashboard/*
```

## Development

```bash
make test        # pytest --cov=src (≥80% coverage on domain + application layers)
make lint        # ruff check + ruff format --check + mypy --strict
make format      # ruff format + ruff check --fix (auto-fix)
make clean       # docker-compose down -v + remove data/
```

### Key conventions

- `from __future__ import annotations` at top of every file.
- Python 3.11, line length 99 (`ruff`).
- Use `structlog` exclusively — never `logging` directly.
- All cross-layer communication via **interfaces (ABCs/Protocols)** and **DTOs**.
- Mock only at infrastructure boundary in tests. Never mock domain internals.
- All `created_at` values must be **timezone-aware UTC**.

## API Endpoints

### Core

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Liveness probe |
| `GET` | `/pipeline/status` | ClickHouse + Parquet connectivity, data freshness |

### Dashboard

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/dashboard/top-repos` | Top repos by WatchEvent count |
| `GET` | `/dashboard/trending` | Trending repos over the past N days |
| `GET` | `/dashboard/shock-movers` | Biggest star gainers and percentage movers in the current window |
| `GET` | `/dashboard/topic-rotation` | Topics accelerating fastest versus the prior matching window |
| `GET` | `/dashboard/news-radar` | External headlines for the current breakout repositories |
| `GET` | `/dashboard/language-breakdown` | Event distribution by primary language |
| `GET` | `/dashboard/topic-breakdown` | Event distribution by repo topic |
| `GET` | `/dashboard/category-summary` | AI/ML category breakdown |
| `GET` | `/dashboard/event-volume` | Hourly event volume time series |

### AI / Search

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/ai/search` | Hybrid lexical/semantic repository discovery |
| `GET` | `/ai/repo-brief` | Grounded brief and why-trending narrative for one repo |
| `GET` | `/ai/repo-compare` | Structured comparison between two repositories |
| `GET` | `/ai/related-repos` | Graph-lite related repository recommendations |
| `GET` | `/ai/market-brief` | Weekly market brief over breakout repos and topic shifts |

The AI endpoints require Ollama models `bge-m3` and `llama3.2:3b`. Pull them when you
want to use the AI features:

```bash
make ai-models
```

## Scheduler

Automated cron jobs for pipeline maintenance. Install with:

```bash
./scheduler/crontab_install.sh               # crons only
./scheduler/crontab_install.sh --with-systemd # crons + systemd long-running services
./scheduler/crontab_install.sh --uninstall    # remove all entries
```

| Script | Schedule (UTC) | Purpose |
|--------|---------------|---------|
| `01_nightly_batch_aggregation.sh` | `0 2 * * *` | Spark batch: Parquet → ClickHouse `repo_star_counts` + `repo_activity_summary` |
| `02_kafka_lag_check.sh` | `*/5 * * * *` | Consumer group lag check, WARN if > 50,000 messages |
| `03_data_freshness_check.sh` | `*/5 * * * *` | ClickHouse `max(created_at)` staleness, WARN if > 10 min |
| `04_parquet_cleanup.sh` | `0 3 * * 0` | Delete Parquet partitions older than 90 days |
| `05_clickhouse_optimize.sh` | `0 4 * * 0` | `OPTIMIZE TABLE FINAL` on all ReplacingMergeTree tables |
| `06_token_validation.sh` | `0 1 * * *` | Validate GitHub API tokens via `/rate_limit`, WARN if quota < 500 |
| `07_repo_metadata_refresh.sh` | `0 6 * * *` | Re-fetch stars/forks/topics for all repos in `data/repos/` |
| `08_health_check.sh` | `*/5 * * * *` | 5-point health check: Docker, Kafka, ClickHouse, Parquet, FastAPI |

Long-running services (`gha-poller`, `gha-spark-streaming`) are managed as systemd units in `scheduler/systemd/`.

State files written to `scheduler/state/` (health, freshness, token status, refresh summary).

---

## AI Relevance Filter

`AiEventFilter` (`src/infrastructure/github/event_filter.py`) decides which events are published to Kafka. A repo passes if:

- Any of its **topics** match `_AI_TOPICS` (e.g. `machine-learning`, `llm`, `deep-learning`)
- **OR** its description contains an `_AI_KEYWORDS` keyword (e.g. `transformer`, `neural network`)
- **OR** its name matches an `_AI_REPO_NAME_PATTERNS` regex

**AND NOT** (bot actor detected **OR** spam signal present).

To add a new AI framework, update the relevant set/list in `event_filter.py`.

## Token Rotation

`PollGithubEventsUseCase` supports comma-separated `GITHUB_API_TOKENS`. When all tokens are rate-limited it raises `RateLimitExceededError` and sleeps until the earliest reset timestamp. ETag caching (`If-None-Match`) skips Kafka publishing on HTTP 304 responses.

## Configuration (`.env`)

| Variable | Required | Description |
|----------|----------|-------------|
| `GITHUB_API_TOKENS` | ✅ | Comma-separated PATs for token rotation |
| `CLICKHOUSE_PASSWORD` | ✅ | ClickHouse `analyst` user password |
| `KAFKA_BOOTSTRAP_SERVERS` | — | default `localhost:9092` |
| `CLICKHOUSE_HOST` | — | default `localhost` |
| `CLICKHOUSE_PORT` | — | default `9100` (host) / `9000` (inside Docker network) |
| `OLLAMA_BASE_URL` | — | default `http://localhost:11435` |
| `OLLAMA_EMBEDDING_MODEL` | — | default `bge-m3` |
| `OLLAMA_GENERATION_MODEL` | — | default `llama3.2:3b` |
| `SEARXNG_BASE_URL` | — | default `http://localhost:8080` |
| `GRAFANA_PASSWORD` | — | default `admin` |
| `SPARK_MASTER` | — | default `local[16]` |
| `SPARK_DRIVER_MEMORY` | — | default `8g` |

---

## Hardware Notes

Tuned for: Intel i7-12700F (20 threads), 32 GB RAM, Linux x86_64.

| Setting | Value | Reason |
|---------|-------|--------|
| `SPARK_MASTER` | `local[16]` | 16 performance cores |
| `SPARK_DRIVER_MEMORY` | `8g` | Fits in 25 GB available |
| `SPARK_EXECUTOR_MEMORY` | `12g` | Headroom for Parquet write buffers |
| Kafka partitions | 16 | Parallelism matches CPU core count |
| Trigger interval | 60s | Balances latency vs overhead |

---
