"""Centralised application configuration via pydantic-settings.

All secrets and runtime parameters are sourced from environment variables
(or a ``.env`` file in the project root during development).
No hardcoded defaults for secrets — those must be set explicitly.
"""

from __future__ import annotations

from datetime import date
from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl, BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ExternalNewsSourceConfig(BaseModel):
    """Configured official external source for news-impact intelligence."""

    provider: str = Field(..., min_length=1)
    url: AnyHttpUrl
    source_type: Literal["rss", "atom", "json", "html"] = "rss"
    enabled: bool = True


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

    github_api_tokens: str = Field(..., description="Comma-separated bearer tokens.")
    github_api_base_url: AnyHttpUrl = Field(
        default="https://api.github.com",  # type: ignore[assignment]
        description="GitHub API base URL (override for testing).",
    )
    poll_interval_seconds: float = Field(
        default=0.5,
        ge=0.5,
        description="Seconds between GitHub API poll iterations.",
    )

    @property
    def github_tokens_list(self) -> list[str]:
        """Return the comma-separated token string as a list."""
        raw = self.github_api_tokens.strip().strip('"').strip("'")
        return [token.strip() for token in raw.split(",") if token.strip()]

    kafka_bootstrap_servers: str = Field(
        default="localhost:9092",
        description="Comma-separated Kafka bootstrap server addresses.",
    )
    kafka_topic: str = Field(default="github_raw_events")
    kafka_retention_hours: int = Field(default=168, ge=1)

    clickhouse_host: str = Field(default="localhost")
    clickhouse_port: int = Field(default=9000, ge=1, le=65535)
    clickhouse_user: str = Field(default="analyst")
    clickhouse_password: str = Field(..., description="ClickHouse password.")
    clickhouse_database: str = Field(default="github_analyzer")

    parquet_base_path: str = Field(default="./data/raw")
    checkpoint_base_path: str = Field(default="./data/checkpoints")

    spark_master: str = Field(default="local[16]")
    spark_driver_memory: str = Field(default="8g")
    spark_executor_memory: str = Field(default="12g")
    spark_parquet_max_records_per_file: int = Field(default=50_000, ge=1)
    spark_parquet_target_partitions_per_batch: int = Field(default=8, ge=1)

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
    news_intelligence_mode: Literal["curated", "hybrid", "live"] = Field(
        default="curated",
        description="Serving mode for the NewsImpact intelligence surface.",
    )
    news_intelligence_sync_enabled: bool = Field(
        default=False,
        description="Whether external-source sync for NewsImpact is enabled.",
    )
    news_intelligence_sources: list[ExternalNewsSourceConfig] = Field(
        default_factory=list,
        description="Configured official external sources for news-impact ingestion.",
    )

    log_level: str = Field(default="INFO")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached singleton Settings instance."""
    return Settings()
