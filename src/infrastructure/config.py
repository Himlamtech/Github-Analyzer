"""Application settings loaded from environment variables."""

from __future__ import annotations

from datetime import date
from functools import lru_cache

from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for API, storage, AI, and observability services."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    log_level: str = "INFO"

    clickhouse_host: str = "localhost"
    clickhouse_port: int = Field(default=9000, ge=1, le=65535)
    clickhouse_user: str = "default"
    clickhouse_password: str = ""
    clickhouse_database: str = "github_analyzer"

    parquet_base_path: str = "./data/raw"
    checkpoint_base_path: str = "./data/checkpoints"
    repo_catalog_path: str = "./data/catalog"
    repo_metadata_path: str = "./data/repos"

    github_api_base_url: AnyHttpUrl = "https://api.github.com"  # type: ignore[assignment]
    github_api_tokens: str = ""
    repo_discovery_start_date: date = date(2026, 1, 1)
    repo_discovery_min_stars: int = Field(default=1000, ge=1)
    repo_discovery_max_shard_size: int = Field(default=100, ge=1, le=1000)

    ai_search_semantic_enabled: bool = True
    ai_search_candidate_limit: int = Field(default=50, ge=10, le=500)
    ai_search_default_limit: int = Field(default=10, ge=1, le=20)
    ai_search_embedding_timeout_seconds: float = Field(default=30.0, ge=1.0)
    ai_repo_brief_llm_enabled: bool = True
    ai_market_brief_llm_enabled: bool = True
    ai_repo_brief_timeout_seconds: float = Field(default=60.0, ge=1.0)

    ollama_base_url: AnyHttpUrl = "http://localhost:11434"  # type: ignore[assignment]
    ollama_embedding_model: str = "nomic-embed-text"
    ollama_generation_model: str = "llama3.1"

    metrics_enabled: bool = True
    metrics_port: int = Field(default=9091, ge=1024, le=65535)
    pipeline_stale_threshold_seconds: float = Field(default=300.0, ge=1.0)

    tracing_enabled: bool = True
    tracing_service_name: str = "github-ai-analyzer-api"
    tracing_exporter_otlp_endpoint: AnyHttpUrl = "http://localhost:4318/v1/traces"  # type: ignore[assignment]
    tracing_sampling_ratio: float = Field(default=1.0, ge=0.0, le=1.0)
    tracing_grafana_base_url: AnyHttpUrl = "http://localhost:3001"  # type: ignore[assignment]
    tracing_grafana_org_id: int = Field(default=1, ge=1)
    tracing_grafana_tempo_datasource_uid: str = "tempo_ds"
    tracing_grafana_explore_from: str = "now-1h"
    tracing_grafana_explore_to: str = "now"

    grafana_password: str = "admin"

    @property
    def github_tokens_list(self) -> list[str]:
        """Return configured GitHub tokens as a normalized list."""
        return [token.strip() for token in self.github_api_tokens.split(",") if token.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached runtime settings."""
    return Settings()
