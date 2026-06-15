# GitHub Analyzer

GitHub Analyzer is a real-time GitHub telemetry pipeline with a FastAPI analytics backend and a Vite/React dashboard frontend. The project ingests GitHub events, persists them into ClickHouse and Parquet, and exposes live dashboard endpoints that the frontend now consumes directly.

## Current status

- Backend focus: ingestion flow, storage, and dashboard-serving APIs
- Frontend focus: new Vite dashboard under `frontend/`
- Integration status: `Overview`, `Breakout Detector`, and runtime status banner are connected to the backend
- Curated views: `News Impact` and `Competitive Radar` remain presentation-oriented research views

## Architecture

```text
GitHub Events API
  -> PollGithubEventsUseCase
  -> Kafka
  -> Spark Structured Streaming
  -> ClickHouse + Parquet
  -> FastAPI dashboard endpoints
  -> Vite/React frontend
```

Layering rule:

```text
presentation -> application -> domain <- infrastructure
```

## Repository map

- `src/domain`: entities, value objects, repository contracts, domain exceptions
- `src/application`: use cases and DTOs
- `src/infrastructure`: GitHub, Kafka, Spark, ClickHouse, Parquet, config, logging
- `src/presentation/api`: FastAPI routes
- `frontend`: Vite/React dashboard
- `docs`: project, backend, frontend, database, design, technique, integration, use-case docs

## Frontend/backend connection

The frontend calls these endpoints directly:

- `GET /pipeline/status`
- `GET /events/latest`
- `GET /dashboard/top-repos`
- `GET /dashboard/trending`
- `GET /dashboard/topic-rotation`
- `GET /dashboard/repo-timeseries`

Frontend environment:

```bash
cp frontend/.env.example frontend/.env
```

Key variable:

- `VITE_API_BASE_URL=http://localhost:8000`

## Local development

### Prerequisites

- `uv`
- Python `3.14`
- Docker + Docker Compose
- Node.js `20+` for local frontend build tooling

### Backend setup

```bash
cp .env.example .env
uv sync
make setup
```

### Run pipeline jobs

```bash
make stream
make process
```

### Run frontend locally

```bash
cd frontend
npm install
npm run dev
```

### Quality gates

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest -v

cd frontend
npm run type-check
npm run build
```

## Docker services

- Frontend: `http://localhost:3000`
- FastAPI: `http://localhost:8000`
- Kafka: `localhost:9092`
- ClickHouse HTTP: `localhost:8123`
- ClickHouse native: `localhost:9000`

## Documentation index

- [Project docs](docs/README.md)
- [Project overview](docs/project.md)
- [Backend](docs/backend.md)
- [Frontend](docs/frontend.md)
- [Database](docs/database.md)
- [Technique](docs/technique.md)
- [Use cases](docs/usecases.md)
- [Design](docs/design.md)
- [Integration](docs/integration.md)
