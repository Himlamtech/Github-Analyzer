"""Centralised application configuration via pydantic-settings.

All secrets and runtime parameters are sourced from environment variables
(or a ``.env`` file in the project root during development).
No hardcoded defaults for secrets — those must be set explicitly.
"""

from __future__ import annotations

from datetime import date
from functools import lru_cache

from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application-wide configuration.

    Populated from environment variables (case-insensitive).
    A ``.env`` file in the working directory is loaded automatically.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── GitHub API ────────────────────────────────────────────────────────────
    # Stored as a raw string in .env (comma-separated); split_tokens() parses it.
    github_api_tokens: str = Field(..., description="Comma-separated bearer tokens.")
    github_api_base_url: AnyHttpUrl = Field(
        default="https://api.github.com",  # type: ignore[assignment]
        description="GitHub API base URL (override for testing).",
    )
    poll_interval_seconds: float = Field(
        default=0.5,
        ge=0.5,
        description="Seconds between GitHub API poll iterations (0.5 = max rate for 2 tokens).",
    )

    @property
    def github_tokens_list(self) -> list[str]:
        """Return the comma-separated token string as a list."""
        raw = self.github_api_tokens.strip().strip('"').strip("'")
        return [t.strip() for t in raw.split(",") if t.strip()]

    # ── Kafka ─────────────────────────────────────────────────────────────────
    kafka_bootstrap_servers: str = Field(
        default="localhost:9092",
        description="Comma-separated Kafka bootstrap server addresses.",
    )
    kafka_topic: str = Field(default="github_raw_events")
    kafka_retention_hours: int = Field(default=168, ge=1)

    # ── ClickHouse ────────────────────────────────────────────────────────────
    clickhouse_host: str = Field(default="localhost")
    clickhouse_port: int = Field(default=9000, ge=1, le=65535)
    clickhouse_user: str = Field(default="analyst")
    clickhouse_password: str = Field(..., description="ClickHouse password.")
    clickhouse_database: str = Field(default="github_analyzer")

    # ── Storage ───────────────────────────────────────────────────────────────
    parquet_base_path: str = Field(default="./data/raw")
    checkpoint_base_path: str = Field(default="./data/checkpoints")

    # ── Spark ─────────────────────────────────────────────────────────────────
    spark_master: str = Field(default="local[16]")
    spark_driver_memory: str = Field(default="8g")
    spark_executor_memory: str = Field(default="12g")

    # ── Repo Metadata ─────────────────────────────────────────────────────────
    repo_metadata_path: str = Field(
        default="./data/repos",
        description="Directory containing *.json repo metadata files from GitHub API.",
    )
    repo_catalog_path: str = Field(
        default="./data/repo_catalog",
        description="Directory containing durable repository catalog snapshots.",
    )
    repo_discovery_min_stars: int = Field(
        default=10_000,
        ge=1,
        description="Minimum stars for repo-first discovery catalog acquisition.",
    )
    repo_discovery_max_shard_size: int = Field(
        default=900,
        ge=1,
        le=1000,
        description="Maximum GitHub Search results per shard before recursive splitting.",
    )
    repo_discovery_start_date: date = Field(
        default=date(2007, 10, 29),
        description="Earliest repository creation date to include in discovery shards.",
    )

    # ── AI Search ─────────────────────────────────────────────────────────────
    ollama_base_url: AnyHttpUrl = Field(
        default="http://localhost:11434",  # type: ignore[assignment]
        description="Base URL for the Ollama HTTP API.",
    )
    ollama_embedding_model: str = Field(
        default="bge-m3",
        description="Embedding model name used for semantic search reranking.",
    )
    ollama_generation_model: str = Field(
        default="llama3.2:3b",
        description="Text generation model used for grounded AI repo briefs.",
    )
    ai_search_semantic_enabled: bool = Field(
        default=True,
        description="Enable semantic reranking via Ollama embeddings when available.",
    )
    ai_search_candidate_limit: int = Field(
        default=40,
        ge=10,
        le=200,
        description="Maximum number of candidate repositories loaded before reranking.",
    )
    ai_search_default_limit: int = Field(
        default=8,
        ge=1,
        le=20,
        description="Default number of AI search results returned by the API.",
    )
    ai_search_embedding_timeout_seconds: float = Field(
        default=20.0,
        ge=1.0,
        le=120.0,
        description="HTTP timeout for Ollama embedding requests in seconds.",
    )
    ai_repo_brief_llm_enabled: bool = Field(
        default=True,
        description="Enable Ollama-backed generation for repo briefs before template fallback.",
    )
    ai_market_brief_llm_enabled: bool = Field(
        default=True,
        description="Enable Ollama-backed generation for market briefs before template fallback.",
    )
    ai_repo_brief_timeout_seconds: float = Field(
        default=30.0,
        ge=1.0,
        le=120.0,
        description="HTTP timeout for Ollama repo brief generation requests in seconds.",
    )
    searxng_base_url: AnyHttpUrl = Field(
        default="http://localhost:8080",  # type: ignore[assignment]
        description="Base URL for the SearXNG instance used by the news radar.",
    )
    searxng_timeout_seconds: float = Field(
        default=10.0,
        ge=1.0,
        le=120.0,
        description="HTTP timeout for SearXNG news lookups in seconds.",
    )
    searxng_news_limit: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum external headlines returned per repository.",
    )

    # ── Observability ─────────────────────────────────────────────────────────
    metrics_port: int = Field(default=9091, ge=1024, le=65535)
    tracing_enabled: bool = Field(
        default=True,
        description="Enable OpenTelemetry tracing export to Tempo via OTLP/HTTP.",
    )
    tracing_sampling_ratio: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Trace sampling ratio for API requests.",
    )
    tracing_service_name: str = Field(
        default="gha-api",
        description="OpenTelemetry service.name exported to the tracing backend.",
    )
    tracing_exporter_otlp_endpoint: AnyHttpUrl = Field(
        default="http://localhost:4318/v1/traces",  # type: ignore[assignment]
        description="OTLP/HTTP trace ingestion endpoint.",
    )
    tracing_grafana_base_url: AnyHttpUrl = Field(
        default="http://localhost:3001",  # type: ignore[assignment]
        description="Base URL of the Grafana instance used for trace drilldown links.",
    )
    tracing_grafana_org_id: int = Field(
        default=1,
        ge=1,
        description="Grafana organization ID used when building Explore links.",
    )
    tracing_grafana_tempo_datasource_uid: str = Field(
        default="tempo_ds",
        min_length=1,
        description="Grafana Tempo datasource UID used for trace drilldown links.",
    )
    tracing_grafana_explore_from: str = Field(
        default="now-1h",
        min_length=1,
        description="Default Grafana Explore start range for trace drilldown links.",
    )
    tracing_grafana_explore_to: str = Field(
        default="now",
        min_length=1,
        description="Default Grafana Explore end range for trace drilldown links.",
    )
    log_level: str = Field(default="INFO")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached singleton Settings instance.

    Using ``lru_cache`` ensures the ``.env`` file is parsed only once
    during the process lifetime.
    """
    return Settings()
