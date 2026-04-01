"""Runtime settings for backend services."""

from __future__ import annotations

from functools import lru_cache

from pydantic import HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    log_level: str = "INFO"

    clickhouse_host: str = "localhost"
    clickhouse_port: int = 9000
    clickhouse_user: str = "default"
    clickhouse_password: str = ""
    clickhouse_database: str = "github_analyzer"

    parquet_base_path: str = "data/raw"
    checkpoint_base_path: str = "data/checkpoints"
    repo_catalog_path: str = "data/catalog/repos.json"
    repo_metadata_path: str = "data/catalog/repo_metadata.json"

    ai_search_semantic_enabled: bool = True
    ai_search_candidate_limit: int = 50
    ai_search_default_limit: int = 10
    ai_search_embedding_timeout_seconds: int = 30

    ai_repo_brief_llm_enabled: bool = True
    ai_market_brief_llm_enabled: bool = True
    ai_repo_brief_timeout_seconds: int = 60

    ollama_base_url: HttpUrl = "http://localhost:11434"  # type: ignore[assignment]
    ollama_embedding_model: str = "nomic-embed-text"
    ollama_generation_model: str = "llama3.1"

    tracing_enabled: bool = True
    tracing_service_name: str = "github-ai-analyzer-api"
    tracing_exporter_otlp_endpoint: HttpUrl = "http://localhost:4318"  # type: ignore[assignment]
    tracing_sampling_ratio: float = 1.0


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings."""

    return Settings()
