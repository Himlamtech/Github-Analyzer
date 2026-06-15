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
        include_quarantined: bool = False,
    ) -> list[ExternalNewsPreviewItemDTO]:
        rows = await self._repository.list_latest_items(
            provider=provider,
            limit=limit,
            include_quarantined=include_quarantined,
        )
        return [
            ExternalNewsPreviewItemDTO(
                source_id=str(row["source_id"]),
                provider=str(row["provider"]),
                title=str(row["title"]),
                url=str(row["url"]),
                published_at=cast("datetime", row["published_at"]),
                summary=str(row["summary"]),
                event_type=str(row.get("event_type") or "news"),
                linked_entities=[
                    str(item) for item in cast("list[object]", row.get("linked_entities") or [])
                ],
                linked_categories=[
                    str(item) for item in cast("list[object]", row.get("linked_categories") or [])
                ],
                linked_repos=[
                    str(item)
                    for item in cast("list[object]", row.get("linked_repo_full_names") or [])
                ],
                linked_frameworks=[
                    str(item)
                    for item in cast("list[object]", row.get("linked_framework_ids") or [])
                ],
                quality_score=float(cast("int | float | str", row.get("quality_score") or 0.0)),
                is_quarantined=bool(row.get("is_quarantined") or False),
                quarantine_reason=(
                    None
                    if row.get("quarantine_reason") is None
                    else str(row.get("quarantine_reason"))
                ),
            )
            for row in rows
        ]


class GetPersistedExternalNewsItemUseCase:
    """Return one persisted external news item for detailed API presentation."""

    def __init__(self, repository: ExternalNewsRepositoryABC) -> None:
        self._repository = repository

    async def execute(self, source_id: str) -> ExternalNewsPreviewItemDTO | None:
        row = await self._repository.get_item_by_source_id(source_id)
        if row is None:
            return None

        return ExternalNewsPreviewItemDTO(
            source_id=str(row["source_id"]),
            provider=str(row["provider"]),
            title=str(row["title"]),
            url=str(row["url"]),
            published_at=cast("datetime", row["published_at"]),
            summary=str(row["summary"]),
            event_type=str(row.get("event_type") or "news"),
            linked_entities=[
                str(item) for item in cast("list[object]", row.get("linked_entities") or [])
            ],
            linked_categories=[
                str(item) for item in cast("list[object]", row.get("linked_categories") or [])
            ],
            linked_repos=[
                str(item) for item in cast("list[object]", row.get("linked_repo_full_names") or [])
            ],
            linked_frameworks=[
                str(item) for item in cast("list[object]", row.get("linked_framework_ids") or [])
            ],
            quality_score=float(cast("int | float | str", row.get("quality_score") or 0.0)),
            is_quarantined=bool(row.get("is_quarantined") or False),
            quarantine_reason=(
                None if row.get("quarantine_reason") is None else str(row.get("quarantine_reason"))
            ),
        )


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
