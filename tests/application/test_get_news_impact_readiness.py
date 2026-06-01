"""Tests for the news-impact readiness use case."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from src.application.use_cases.get_news_impact_readiness import (
    GetNewsImpactReadinessUseCase,
)
from src.infrastructure.config import ExternalNewsSourceConfig, Settings


class FakeExternalNewsRepository:
    def __init__(self, rows: list[dict[str, object]] | None = None) -> None:
        self._rows = rows or []

    async def list_latest_source_health(self) -> list[dict[str, object]]:
        return self._rows


async def test_execute_returns_partial_when_sync_is_disabled_and_no_sources() -> None:
    settings = Settings(
        github_api_tokens="test-token",
        clickhouse_password="test-password",
    )

    result = await GetNewsImpactReadinessUseCase(settings=settings).execute()

    assert result.mode == "curated"
    assert result.status == "partial"
    assert result.freshness_status == "unknown"
    assert result.configured_source_count == 0
    assert result.missing_requirements


async def test_execute_returns_ready_when_sources_are_enabled_and_fresh() -> None:
    settings = Settings(
        github_api_tokens="test-token",
        clickhouse_password="test-password",
        news_intelligence_mode="hybrid",
        news_intelligence_sync_enabled=True,
        news_intelligence_sources=[
            ExternalNewsSourceConfig(
                provider="OpenAI",
                url="https://openai.com/news/rss.xml",
                source_type="rss",
                enabled=True,
            )
        ],
    )
    repository = FakeExternalNewsRepository(
        [
            {
                "provider": "OpenAI",
                "source_url": "https://openai.com/news/rss.xml",
                "status": "ok",
                "fetched_count": 2,
                "error_message": None,
                "checked_at": datetime.now(tz=UTC) - timedelta(minutes=30),
            }
        ]
    )

    result = await GetNewsImpactReadinessUseCase(
        settings=settings,
        repository=repository,
    ).execute()

    assert result.status == "ready"
    assert result.enabled_source_count == 1
    assert result.healthy_source_count == 1
    assert result.stale_source_count == 0
    assert result.freshness_status == "healthy"
    assert result.sources[0].freshness_status == "healthy"
    assert not result.missing_requirements


async def test_execute_returns_partial_when_enabled_source_is_stale() -> None:
    settings = Settings(
        github_api_tokens="test-token",
        clickhouse_password="test-password",
        news_intelligence_mode="hybrid",
        news_intelligence_sync_enabled=True,
        news_intelligence_sources=[
            ExternalNewsSourceConfig(
                provider="Anthropic",
                url="https://www.anthropic.com/news/rss.xml",
                source_type="rss",
                enabled=True,
            )
        ],
    )
    repository = FakeExternalNewsRepository(
        [
            {
                "provider": "Anthropic",
                "source_url": "https://www.anthropic.com/news/rss.xml",
                "status": "ok",
                "fetched_count": 1,
                "error_message": None,
                "checked_at": datetime.now(tz=UTC) - timedelta(hours=5),
            }
        ]
    )

    result = await GetNewsImpactReadinessUseCase(
        settings=settings,
        repository=repository,
    ).execute()

    assert result.status == "partial"
    assert result.freshness_status == "stale"
    assert result.stale_source_count == 1
    assert "fresh successful sync" in result.missing_requirements[0]


async def test_execute_returns_blocked_when_live_mode_has_no_enabled_sources() -> None:
    settings = Settings(
        github_api_tokens="test-token",
        clickhouse_password="test-password",
        news_intelligence_mode="live",
        news_intelligence_sync_enabled=True,
        news_intelligence_sources=[
            ExternalNewsSourceConfig(
                provider="Anthropic",
                url="https://www.anthropic.com/news/rss.xml",
                source_type="rss",
                enabled=False,
            )
        ],
    )

    result = await GetNewsImpactReadinessUseCase(settings=settings).execute()

    assert result.status == "blocked"
    assert result.enabled_source_count == 0
    assert result.freshness_status == "unknown"
    assert "Live mode requires at least one enabled official external source." in (
        result.missing_requirements
    )
