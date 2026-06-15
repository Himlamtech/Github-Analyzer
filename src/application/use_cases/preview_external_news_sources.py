"""Preview official external news sources configured for NewsImpact."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import structlog

from src.application.dtos.intelligence_dto import (
    ExternalNewsPreviewItemDTO,
    ExternalNewsSourcePreviewDTO,
)
from src.domain.exceptions import ExternalSourceError

if TYPE_CHECKING:
    from src.domain.repositories.external_news_reader import ExternalNewsReaderABC
    from src.infrastructure.config import ExternalNewsSourceConfig, Settings

logger = structlog.get_logger(__name__)


class PreviewExternalNewsSourcesUseCase:
    """Fetch the latest items from enabled official external news sources.

    Nguồn nào thất bại sẽ trả về items=[] và error message, không làm crash toàn bộ response.
    """

    def __init__(self, reader: ExternalNewsReaderABC, settings: Settings) -> None:
        self._reader = reader
        self._settings = settings

    async def execute(self, limit_per_source: int = 3) -> list[ExternalNewsSourcePreviewDTO]:
        enabled_sources: list[ExternalNewsSourceConfig] = [
            source for source in self._settings.news_intelligence_sources if source.enabled
        ]

        async def _fetch_one(source: ExternalNewsSourceConfig) -> ExternalNewsSourcePreviewDTO:
            try:
                items = await self._reader.fetch_latest(
                    provider=source.provider,
                    url=str(source.url),
                    source_type=source.source_type,
                    limit=limit_per_source,
                )
                return ExternalNewsSourcePreviewDTO(
                    provider=source.provider,
                    url=str(source.url),
                    source_type=source.source_type,
                    items=[
                        ExternalNewsPreviewItemDTO(
                            source_id=item.source_id,
                            provider=item.provider,
                            title=item.title,
                            url=item.url,
                            published_at=item.published_at,
                            summary=item.summary,
                        )
                        for item in items
                    ],
                )
            except ExternalSourceError as exc:
                logger.warning(
                    "preview_external_news_sources.source_failed",
                    provider=source.provider,
                    error=str(exc),
                )
                return ExternalNewsSourcePreviewDTO(
                    provider=source.provider,
                    url=str(source.url),
                    source_type=source.source_type,
                    items=[],
                    error=str(exc),
                )

        return list(await asyncio.gather(*(_fetch_one(s) for s in enabled_sources)))
