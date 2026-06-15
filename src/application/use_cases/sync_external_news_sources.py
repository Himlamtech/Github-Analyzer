"""Sync enabled official external news sources into persistence."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from hashlib import sha1
from typing import TYPE_CHECKING

from src.application.dtos.intelligence_dto import (
    ExternalNewsSourceHealthDTO,
    ExternalNewsSyncResultDTO,
)
from src.application.intelligence_taxonomy import (
    compute_quality_score,
    infer_categories,
    infer_entities,
    infer_event_type,
    infer_linked_frameworks,
    infer_linked_repos,
    should_quarantine,
)
from src.domain.entities.external_news_item import ExternalNewsItem
from src.domain.exceptions import ExternalSourceError

if TYPE_CHECKING:
    from src.domain.repositories.external_news_reader import ExternalNewsReaderABC
    from src.domain.repositories.external_news_repository import ExternalNewsRepositoryABC
    from src.infrastructure.config import ExternalNewsSourceConfig, Settings


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
        enabled_sources: list[ExternalNewsSourceConfig] = [
            source for source in self._settings.news_intelligence_sources if source.enabled
        ]

        async def _fetch_one(
            source: ExternalNewsSourceConfig,
        ) -> tuple[ExternalNewsSourceConfig, list[ExternalNewsItem], datetime, str | None]:
            checked_at = datetime.now(tz=UTC)
            try:
                raw_items = await self._reader.fetch_latest(
                    provider=source.provider,
                    url=str(source.url),
                    source_type=source.source_type,
                    limit=limit_per_source,
                )
                return source, raw_items, checked_at, None
            except ExternalSourceError as exc:
                return source, [], checked_at, str(exc)

        fetch_results = await asyncio.gather(*(_fetch_one(s) for s in enabled_sources))

        persisted_total = 0
        quarantined_total = 0
        health_rows: list[ExternalNewsSourceHealthDTO] = []
        seen_keys: set[str] = set()

        for source, raw_items, checked_at, error in fetch_results:
            if error is not None:
                health = ExternalNewsSourceHealthDTO(
                    provider=source.provider,
                    source_url=str(source.url),
                    status="error",
                    fetched_count=0,
                    error_message=error,
                    checked_at=checked_at,
                )
            else:
                items = self._enrich_items(
                    raw_items,
                    provider=source.provider,
                    source_type=source.source_type,
                    seen_keys=seen_keys,
                )
                persisted_count = await self._repository.upsert_items(items)
                persisted_total += persisted_count
                quarantined_total += sum(1 for item in items if item.is_quarantined)
                health = ExternalNewsSourceHealthDTO(
                    provider=source.provider,
                    source_url=str(source.url),
                    status="ok",
                    fetched_count=len(items),
                    error_message=None,
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
            quarantined_item_count=quarantined_total,
            source_health=health_rows,
        )

    def _enrich_items(
        self,
        items: list[ExternalNewsItem],
        *,
        provider: str,
        source_type: str,
        seen_keys: set[str],
    ) -> list[ExternalNewsItem]:
        enriched: list[ExternalNewsItem] = []
        for item in items:
            fingerprint = self._fingerprint(item.title, item.url)
            duplicate = fingerprint in seen_keys
            seen_keys.add(fingerprint)
            quality_score = compute_quality_score(item.title, item.summary)
            quarantine_reason = should_quarantine(
                title=item.title,
                url=item.url,
                quality_score=quality_score,
                duplicate=duplicate,
            )
            enriched.append(
                ExternalNewsItem(
                    source_id=item.source_id,
                    provider=item.provider,
                    title=item.title,
                    url=item.url,
                    published_at=item.published_at,
                    summary=item.summary,
                    source_type=source_type,
                    event_type=infer_event_type(item.title, item.summary),
                    linked_entities=tuple(infer_entities(provider, item.title, item.summary)),
                    linked_categories=tuple(infer_categories(item.title, item.summary)),
                    linked_repo_full_names=tuple(
                        infer_linked_repos(provider, item.title, item.summary)
                    ),
                    linked_framework_ids=tuple(
                        infer_linked_frameworks(provider, item.title, item.summary)
                    ),
                    quality_score=quality_score,
                    is_quarantined=quarantine_reason is not None,
                    quarantine_reason=quarantine_reason,
                )
            )
        return enriched

    @staticmethod
    def _fingerprint(title: str, url: str) -> str:
        raw = f"{title.strip().lower()}|{url.strip().lower()}"
        return sha1(raw.encode("utf-8")).hexdigest()
