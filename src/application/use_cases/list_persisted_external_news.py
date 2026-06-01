"""Read persisted external news items and latest source health."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, cast

from src.application.dtos.intelligence_dto import (
    ExternalNewsPreviewItemDTO,
    ExternalNewsSourceHealthDTO,
)

if TYPE_CHECKING:
    from src.domain.repositories.external_news_repository import ExternalNewsRepositoryABC


class ListPersistedExternalNewsItemsUseCase:
    """Return latest persisted external news items for API presentation."""

    def __init__(self, repository: ExternalNewsRepositoryABC) -> None:
        self._repository = repository

    async def execute(
        self,
        *,
        provider: str | None = None,
        limit: int = 20,
    ) -> list[ExternalNewsPreviewItemDTO]:
        rows = await self._repository.list_latest_items(provider=provider, limit=limit)
        return [
            ExternalNewsPreviewItemDTO(
                source_id=str(row["source_id"]),
                provider=str(row["provider"]),
                title=str(row["title"]),
                url=str(row["url"]),
                published_at=cast("datetime", row["published_at"]),
                summary=str(row["summary"]),
            )
            for row in rows
        ]


class ListExternalNewsSourceHealthUseCase:
    """Return latest persisted health snapshots for external news sources."""

    def __init__(self, repository: ExternalNewsRepositoryABC) -> None:
        self._repository = repository

    async def execute(self) -> list[ExternalNewsSourceHealthDTO]:
        rows = await self._repository.list_latest_source_health()
        results: list[ExternalNewsSourceHealthDTO] = []
        for row in rows:
            checked_at = cast("datetime | None", row["checked_at"])
            if checked_at is None:
                checked_at = datetime.now(tz=UTC)
            results.append(
                ExternalNewsSourceHealthDTO(
                    provider=str(row["provider"]),
                    source_url=str(row["source_url"]),
                    status=str(row["status"]),
                    fetched_count=int(cast("int | float | str", row["fetched_count"])),
                    error_message=(
                        None if row["error_message"] is None else str(row["error_message"])
                    ),
                    checked_at=checked_at,
                )
            )
        return results
