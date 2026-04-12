.PHONY: setup ai-models bootstrap-clickhouse stream process query monitor discover-repos sync-repos frontend-dev frontend-build frontend-type-check test lint format clean help

CONDA_ENV := github
PYTHON := conda run -n $(CONDA_ENV) python
PYTEST := conda run -n $(CONDA_ENV) pytest
RUFF   := conda run -n $(CONDA_ENV) ruff
MYPY   := conda run -n $(CONDA_ENV) mypy

# Use locally installed Java 17 (no root required); falls back to system Java
JAVA_HOME_LOCAL := $(HOME)/.local/jdk17
export JAVA_HOME := $(JAVA_HOME_LOCAL)
export PATH := $(JAVA_HOME_LOCAL)/bin:$(PATH)

DATA_DIR       := ./data
CHECKPOINT_DIR := ./data/checkpoints
PARQUET_DIR    := ./data/raw

## ── Infrastructure ──────────────────────────────────────────────────────────

setup: ## Bring up Docker stack, create Kafka topic, init ClickHouse tables
	@mkdir -p $(DATA_DIR) $(CHECKPOINT_DIR) $(PARQUET_DIR)
	@echo "▶ Starting Docker services..."
	docker compose up -d zookeeper kafka clickhouse prometheus grafana ollama qdrant api frontend
	@echo "▶ Waiting for Kafka to be healthy..."
	@until docker compose exec -T kafka kafka-broker-api-versions --bootstrap-server localhost:9092 > /dev/null 2>&1; do \
		echo "  Kafka not ready, retrying in 5s..."; sleep 5; done
	@echo "▶ Creating Kafka topic..."
	docker compose exec -T kafka kafka-topics --create \
		--if-not-exists \
		--bootstrap-server localhost:9092 \
		--topic github_raw_events \
		--partitions 16 \
		--replication-factor 1 \
		--config retention.ms=604800000
	@echo "▶ Waiting for ClickHouse to be healthy..."
	@until docker compose exec -T clickhouse wget -q --spider http://localhost:8123/ping > /dev/null 2>&1; do \
		echo "  ClickHouse not ready, retrying in 5s..."; sleep 5; done
	@echo "▶ Waiting for Ollama to be healthy..."
	@until docker compose exec -T ollama ollama list > /dev/null 2>&1; do \
		echo "  Ollama not ready, retrying in 5s..."; sleep 5; done
	@echo "▶ ClickHouse tables initialized via init.sql (auto on container start)"
	@echo "▶ Ollama is healthy. Pull models on demand with: make ai-models"
	@echo "✓ Setup complete."

ai-models: ## Pull Ollama models required by semantic search and grounded briefs
	@echo "▶ Pulling Ollama models (bge-m3, llama3.2:3b)..."
	docker compose exec -T ollama ollama pull bge-m3
	docker compose exec -T ollama ollama pull llama3.2:3b

bootstrap-clickhouse: ## Backfill ClickHouse github_data from local Parquet archive
	@echo "▶ Bootstrapping ClickHouse github_data from Parquet..."
	$(PYTHON) scripts/backfill_clickhouse_from_parquet.py

## ── Pipeline ────────────────────────────────────────────────────────────────

stream: ## Start GitHub API poller → Kafka producer (runs continuously)
	@echo "▶ Starting GitHub events poller..."
	$(PYTHON) -m src.application.use_cases.poll_github_events

process: ## Start Spark Structured Streaming job (Kafka → Parquet + ClickHouse)
	@echo "▶ Starting Spark Structured Streaming job..."
	$(PYTHON) -m src.application.use_cases.process_event_stream

query: ## Launch DuckDB interactive shell on Parquet files
	@echo "▶ Opening DuckDB shell on $(PARQUET_DIR)..."
	$(PYTHON) -c "import duckdb; duckdb.connect(':memory:').execute(\"SELECT * FROM read_parquet('$(PARQUET_DIR)/**/*.parquet', hive_partitioning=true, union_by_name=true) LIMIT 10\").show()"
	@echo "Tip: Run 'python -m src.infrastructure.storage.duckdb_query_service' for interactive mode."

monitor: ## Open Grafana dashboard in browser
	@echo "▶ Opening Grafana at http://localhost:3001 (admin / \$$GRAFANA_PASSWORD)"
	@xdg-open http://localhost:3001 2>/dev/null || open http://localhost:3001 2>/dev/null || \
		echo "Navigate to http://localhost:3001"

## ── Phase 2 ─────────────────────────────────────────────────────────────────

discover-repos: ## Build or refresh the high-star repository catalog from GitHub Search
	@echo "▶ Discovering repository catalog..."
	$(PYTHON) -m src.application.use_cases.discover_repo_catalog

sync-repos: ## Sync data/repos/*.json → ClickHouse repo_metadata + history tables
	@echo "▶ Syncing repo metadata to ClickHouse..."
	$(PYTHON) -m src.application.use_cases.sync_repo_metadata

sync-events-repos: ## Enrich repo_metadata from top repos in github_data (calls GitHub API)
	@echo "▶ Enriching repo_metadata from active event stream..."
	$(PYTHON) scripts/enrich_repos_from_events.py --limit 200

enrich-repos: ## One-shot enrichment script: top repos from events → repo_metadata (standalone)
	@echo "▶ Running standalone repo enrichment script..."
	$(PYTHON) scripts/enrich_repos_from_events.py --limit 100

frontend-dev: ## Start Next.js dev server on http://localhost:3000
	@echo "▶ Starting Next.js dev server..."
	cd frontend && npm run dev

frontend-build: ## Build Next.js production bundle
	@echo "▶ Building Next.js frontend..."
	cd frontend && npm run build

frontend-type-check: ## Run TypeScript type checker on frontend
	@echo "▶ Type-checking frontend..."
	cd frontend && npm run type-check

## ── Quality ─────────────────────────────────────────────────────────────────

test: ## Run test suite with coverage
	$(PYTEST) tests/ -v --cov=src --cov-report=term-missing --cov-report=html:htmlcov

lint: ## Run ruff linter + formatter check + mypy type checker
	$(RUFF) check src/ tests/
	$(RUFF) format --check src/ tests/
	$(MYPY) src/ --strict

format: ## Auto-format code with ruff
	$(RUFF) format src/ tests/
	$(RUFF) check --fix src/ tests/

## ── Cleanup ─────────────────────────────────────────────────────────────────

clean: ## Stop Docker stack and remove all local data
	@echo "▶ Stopping Docker services..."
	docker compose down -v
	@echo "▶ Removing data directories..."
	rm -rf $(DATA_DIR) htmlcov .coverage .mypy_cache .ruff_cache __pycache__
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	@echo "✓ Clean complete."

## ── Help ────────────────────────────────────────────────────────────────────

help: ## Show this help message
	@echo "GitHub AI Trend Analyzer — available targets:"
	@grep -E '^[a-zA-Z_-]+:.*##' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help
