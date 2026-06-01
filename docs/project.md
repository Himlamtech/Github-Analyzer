# Project

## Overview

GitHub Analyzer ingests GitHub event streams, stores them in ClickHouse and Parquet, and serves a dashboard for telemetry-driven repository analysis.

## Current state

- The backend has been cleaned to focus on data ingestion, transformation, persistence, and dashboard-serving APIs.
- The old frontend has been replaced by a new Vite/React frontend in `frontend/`.
- The dashboard now mixes two kinds of views:
  - live operational analytics powered by FastAPI
  - curated research/presentation views that are intentionally static for now

## Product direction

The current product direction is `AI ecosystem intelligence` built on top of the existing GitHub telemetry pipeline.

Near-term priorities:

1. Keep the serving path simple and stable.
2. Bind the new frontend to trustworthy backend reads before adding new widgets.
3. Add intelligence use cases only when there is a clear analytical model behind them.

The project should avoid shipping UI surfaces that imply strong intelligence features without data contracts, scoring logic, and explainability behind them.

## Repository structure

- `src/domain`: domain entities, value objects, ports, exceptions
- `src/application`: use cases and DTOs
- `src/infrastructure`: external systems and storage adapters
- `src/presentation/api`: FastAPI routes
- `frontend`: Vite dashboard
- `docs`: implementation-facing documentation

## Acceptance state for this phase

- Frontend replacement is the new source of truth
- Frontend can call backend successfully for the core dashboard path
- Docs describe the project as it exists now, not as it used to exist

## Short roadmap

### Phase 0: stabilize the serving path

- Keep `ClickHouse` as the serving source of truth.
- Keep `Parquet` as archive and recovery storage.
- Reduce ambiguity between live views and curated views.

### Phase 1: ship the first intelligence pages properly

- Breakout scoring with a real mart and confidence model
- Ecosystem rotation with category-aware data rather than generic fallback labels

### Phase 2: add source control and external intelligence

- source freshness guard
- external data quarantine
- official launch/news ingestion
