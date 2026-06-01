"""Preview official external news sources configured for NewsImpact."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.application.dtos.intelligence_dto import (
    ExternalNewsPreviewItemDTO,
    ExternalNewsSourcePreviewDTO,
)

if TYPE_CHECKING:
    from src.domain.repositories.external_news_reader import ExternalNewsReaderABC
    from src.infrastructure.config import Settings


class PreviewExternalNewsSourcesUseCase:
    """Fetch the latest items from enabled official external news sources."""

    def __init__(self, reader: ExternalNewsReaderABC, settings: Settings) -> None:
        self._reader = reader
        self._settings = settings

    async def execute(self, limit_per_source: int = 3) -> list[ExternalNewsSourcePreviewDTO]:
        previews: list[ExternalNewsSourcePreviewDTO] = []

        for source in self._settings.news_intelligence_sources:
            if not source.enabled:
                continue
            items = await self._reader.fetch_latest(
                provider=source.provider,
                url=str(source.url),
                source_type=source.source_type,
                limit=limit_per_source,
            )
            previews.append(
                ExternalNewsSourcePreviewDTO(
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
            )

        return previews
