.PHONY: setup bootstrap-clickhouse stream process discover-repos sync-repos frontend-dev frontend-build frontend-type-check test lint format clean help

PYTHON := uv run python
PYTEST := uv run pytest
RUFF   := uv run ruff
MYPY   := uv run mypy

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
	docker compose up -d zookeeper kafka clickhouse api frontend
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
	@echo "▶ ClickHouse tables initialized via init.sql (auto on container start)"
	@echo "✓ Setup complete."

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

cleanup: ## Xoá Parquet partitions cũ hơn 90 ngày (dùng --dry-run để preview)
	@echo "▶ Cleaning up old Parquet partitions..."
	$(PYTHON) -m src.application.use_cases.cleanup_parquet $(ARGS)

cleanup-dry: ## Preview Parquet partitions sẽ bị xoá (không xoá thực tế)
	@echo "▶ Dry run: preview partitions to be deleted..."
	$(PYTHON) -m src.application.use_cases.cleanup_parquet --dry-run $(ARGS)

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

frontend-dev: ## Start Vite dev server on http://localhost:3000
	@echo "▶ Starting Vite dev server..."
	cd frontend && npm run dev

frontend-build: ## Build Vite production bundle
	@echo "▶ Building Vite frontend..."
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
	@echo "GitHub Analyzer — available targets:"
	@grep -E '^[a-zA-Z_-]+:.*##' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help
