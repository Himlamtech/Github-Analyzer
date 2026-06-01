"""Tests for previewing configured external news sources."""

from __future__ import annotations

from datetime import UTC, datetime

from src.application.use_cases.preview_external_news_sources import (
    PreviewExternalNewsSourcesUseCase,
)
from src.domain.entities.external_news_item import ExternalNewsItem
from src.infrastructure.config import ExternalNewsSourceConfig, Settings


class FakeExternalNewsReader:
    async def fetch_latest(
        self,
        *,
        provider: str,
        url: str,
        source_type: str,
        limit: int,
    ) -> list[ExternalNewsItem]:
        del url, source_type
        return [
            ExternalNewsItem(
                source_id=f"{provider.lower()}-1",
                provider=provider,
                title=f"{provider} launch update",
                url="https://example.com/post-1",
                published_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
                summary="Official announcement summary.",
            )
        ][:limit]


async def test_execute_returns_preview_for_enabled_sources_only() -> None:
    settings = Settings(
        github_api_tokens="test-token",
        clickhouse_password="test-password",
        news_intelligence_sources=[
            ExternalNewsSourceConfig(
                provider="OpenAI",
                url="https://openai.com/news/rss.xml",
                source_type="rss",
                enabled=True,
            ),
            ExternalNewsSourceConfig(
                provider="Anthropic",
                url="https://www.anthropic.com/news/rss.xml",
                source_type="rss",
                enabled=False,
            ),
        ],
    )

    result = await PreviewExternalNewsSourcesUseCase(
        reader=FakeExternalNewsReader(),
        settings=settings,
    ).execute(limit_per_source=2)

    assert len(result) == 1
    assert result[0].provider == "OpenAI"
    assert result[0].items[0].source_id == "openai-1"
