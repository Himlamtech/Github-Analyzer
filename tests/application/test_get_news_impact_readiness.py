"""Tests for the news-impact readiness use case."""

from __future__ import annotations

from src.application.use_cases.get_news_impact_readiness import (
    GetNewsImpactReadinessUseCase,
)
from src.infrastructure.config import ExternalNewsSourceConfig, Settings


def test_execute_returns_partial_when_sync_is_disabled_and_no_sources() -> None:
    settings = Settings(
        github_api_tokens="test-token",
        clickhouse_password="test-password",
    )

    result = GetNewsImpactReadinessUseCase(settings=settings).execute()

    assert result.mode == "curated"
    assert result.status == "partial"
    assert result.configured_source_count == 0
    assert result.missing_requirements


def test_execute_returns_ready_when_sources_are_enabled_and_sync_is_on() -> None:
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

    result = GetNewsImpactReadinessUseCase(settings=settings).execute()

    assert result.status == "ready"
    assert result.enabled_source_count == 1
    assert not result.missing_requirements


def test_execute_returns_blocked_when_live_mode_has_no_enabled_sources() -> None:
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

    result = GetNewsImpactReadinessUseCase(settings=settings).execute()

    assert result.status == "blocked"
    assert result.enabled_source_count == 0
    assert "Live mode requires at least one enabled official external source." in (
        result.missing_requirements
    )
