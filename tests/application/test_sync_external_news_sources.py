"""Tests for syncing external news sources into persistence."""

from __future__ import annotations

from datetime import UTC, datetime

from src.application.use_cases.sync_external_news_sources import SyncExternalNewsSourcesUseCase
from src.domain.entities.external_news_item import ExternalNewsItem
from src.domain.exceptions import ExternalSourceError
from src.infrastructure.config import ExternalNewsSourceConfig, Settings


class FakeExternalNewsReader:
    def __init__(self, should_fail: bool = False, duplicate: bool = False) -> None:
        self._should_fail = should_fail
        self._duplicate = duplicate

    async def fetch_latest(
        self,
        *,
        provider: str,
        url: str,
        source_type: str,
        limit: int,
    ) -> list[ExternalNewsItem]:
        del url, source_type
        if self._should_fail:
            raise ExternalSourceError(f"{provider} feed unavailable")
        items = [
            ExternalNewsItem(
                source_id=f"{provider.lower()}-1",
                provider=provider,
                title=f"{provider} browser agent launch",
                url="https://example.com/item-1",
                published_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
                summary="Launch summary for browser automation agents.",
            )
        ]
        if self._duplicate:
            items.append(
                ExternalNewsItem(
                    source_id=f"{provider.lower()}-2",
                    provider=provider,
                    title=f"{provider} browser agent launch",
                    url="https://example.com/item-1",
                    published_at=datetime(2026, 1, 1, 13, 0, tzinfo=UTC),
                    summary="Duplicate launch summary for browser automation agents.",
                )
            )
        return items[:limit]


class FakeExternalNewsRepository:
    def __init__(self) -> None:
        self.saved_items: list[ExternalNewsItem] = []
        self.health_snapshots: list[dict[str, object]] = []

    async def upsert_items(self, items: list[ExternalNewsItem]) -> int:
        self.saved_items.extend(items)
        return len(items)

    async def append_source_health_snapshot(
        self,
        *,
        provider: str,
        source_url: str,
        status: str,
        fetched_count: int,
        error_message: str | None,
        checked_at: datetime,
    ) -> None:
        self.health_snapshots.append(
            {
                "provider": provider,
                "source_url": source_url,
                "status": status,
                "fetched_count": fetched_count,
                "error_message": error_message,
                "checked_at": checked_at,
            }
        )

    async def list_latest_items(
        self,
        *,
        provider: str | None,
        limit: int,
        include_quarantined: bool = False,
    ) -> list[dict[str, object]]:
        del provider, limit, include_quarantined
        return []

    async def get_item_by_source_id(self, source_id: str) -> dict[str, object] | None:
        del source_id
        return None

    async def list_latest_source_health(self) -> list[dict[str, object]]:
        return []


async def test_execute_persists_items_and_health_for_enabled_sources() -> None:
    repository = FakeExternalNewsRepository()
    settings = Settings(
        github_api_tokens="test-token",
        clickhouse_password="test-password",
        news_intelligence_sources=[
            ExternalNewsSourceConfig(
                provider="OpenAI",
                url="https://openai.com/news/rss.xml",
                source_type="rss",
                enabled=True,
            )
        ],
    )

    result = await SyncExternalNewsSourcesUseCase(
        reader=FakeExternalNewsReader(),
        repository=repository,
        settings=settings,
    ).execute(limit_per_source=5)

    assert result.persisted_item_count == 1
    assert result.quarantined_item_count == 0
    assert repository.saved_items[0].provider == "OpenAI"
    assert repository.saved_items[0].event_type == "launch"
    assert repository.saved_items[0].linked_categories == ("Coding Agents & Automation",)
    assert result.source_health[0].status == "ok"


async def test_execute_marks_duplicate_items_as_quarantined() -> None:
    repository = FakeExternalNewsRepository()
    settings = Settings(
        github_api_tokens="test-token",
        clickhouse_password="test-password",
        news_intelligence_sources=[
            ExternalNewsSourceConfig(
                provider="OpenAI",
                url="https://openai.com/news/rss.xml",
                source_type="rss",
                enabled=True,
            )
        ],
    )

    result = await SyncExternalNewsSourcesUseCase(
        reader=FakeExternalNewsReader(duplicate=True),
        repository=repository,
        settings=settings,
    ).execute(limit_per_source=5)

    assert result.persisted_item_count == 2
    assert result.quarantined_item_count == 1
    assert repository.saved_items[1].is_quarantined is True
    assert repository.saved_items[1].quarantine_reason == "duplicate_content"


async def test_execute_records_error_health_when_source_fetch_fails() -> None:
    repository = FakeExternalNewsRepository()
    settings = Settings(
        github_api_tokens="test-token",
        clickhouse_password="test-password",
        news_intelligence_sources=[
            ExternalNewsSourceConfig(
                provider="Anthropic",
                url="https://www.anthropic.com/news/rss.xml",
                source_type="rss",
                enabled=True,
            )
        ],
    )

    result = await SyncExternalNewsSourcesUseCase(
        reader=FakeExternalNewsReader(should_fail=True),
        repository=repository,
        settings=settings,
    ).execute(limit_per_source=5)

    assert result.persisted_item_count == 0
    assert result.source_health[0].status == "error"
    assert "unavailable" in (result.source_health[0].error_message or "")
