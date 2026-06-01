"""Sync enabled official external news sources into persistence."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from src.application.dtos.intelligence_dto import (
    ExternalNewsSourceHealthDTO,
    ExternalNewsSyncResultDTO,
)
from src.domain.exceptions import ExternalSourceError

if TYPE_CHECKING:
    from src.domain.repositories.external_news_reader import ExternalNewsReaderABC
    from src.domain.repositories.external_news_repository import ExternalNewsRepositoryABC
    from src.infrastructure.config import Settings


class SyncExternalNewsSourcesUseCase:
    """Fetch enabled official external feeds and persist their latest items."""

    def __init__(
        self,
        reader: ExternalNewsReaderABC,
        repository: ExternalNewsRepositoryABC,
        settings: Settings,
    ) -> None:
        self._reader = reader
        self._repository = repository
        self._settings = settings

    async def execute(self, limit_per_source: int = 10) -> ExternalNewsSyncResultDTO:
        persisted_total = 0
        health_rows: list[ExternalNewsSourceHealthDTO] = []

        for source in self._settings.news_intelligence_sources:
            if not source.enabled:
                continue

            checked_at = datetime.now(tz=UTC)
            try:
                items = await self._reader.fetch_latest(
                    provider=source.provider,
                    url=str(source.url),
                    source_type=source.source_type,
                    limit=limit_per_source,
                )
                persisted_count = await self._repository.upsert_items(items)
                persisted_total += persisted_count
                health = ExternalNewsSourceHealthDTO(
                    provider=source.provider,
                    source_url=str(source.url),
                    status="ok",
                    fetched_count=len(items),
                    error_message=None,
                    checked_at=checked_at,
                )
            except ExternalSourceError as exc:
                health = ExternalNewsSourceHealthDTO(
                    provider=source.provider,
                    source_url=str(source.url),
                    status="error",
                    fetched_count=0,
                    error_message=str(exc),
                    checked_at=checked_at,
                )

            await self._repository.append_source_health_snapshot(
                provider=health.provider,
                source_url=health.source_url,
                status=health.status,
                fetched_count=health.fetched_count,
                error_message=health.error_message,
                checked_at=health.checked_at,
            )
            health_rows.append(health)

        return ExternalNewsSyncResultDTO(
            persisted_item_count=persisted_total,
            source_health=health_rows,
        )
