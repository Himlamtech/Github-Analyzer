"""Readiness snapshot for external news-impact ingestion."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, cast

from src.application.dtos.intelligence_dto import (
    NewsImpactReadinessDTO,
    NewsImpactSourceDTO,
)

if TYPE_CHECKING:
    from src.domain.repositories.external_news_repository import ExternalNewsRepositoryABC
    from src.infrastructure.config import Settings


class GetNewsImpactReadinessUseCase:
    """Describe whether NewsImpact can move beyond curated snapshots."""

    def __init__(
        self,
        settings: Settings,
        repository: ExternalNewsRepositoryABC | None = None,
    ) -> None:
        self._settings = settings
        self._repository = repository

    async def execute(self) -> NewsImpactReadinessDTO:
        health_by_source = await self._load_health_by_source()
        now = datetime.now(tz=UTC)
        sources = [
            self._build_source_dto(
                provider=source.provider,
                url=str(source.url),
                source_type=source.source_type,
                enabled=source.enabled,
                health=health_by_source.get((source.provider, str(source.url))),
                now=now,
            )
            for source in self._settings.news_intelligence_sources
        ]
        enabled_source_count = sum(1 for source in sources if source.enabled)
        healthy_source_count = sum(1 for source in sources if source.freshness_status == "healthy")
        stale_source_count = sum(1 for source in sources if source.freshness_status == "stale")

        missing_requirements: list[str] = []
        if not sources:
            missing_requirements.append("No official external news sources configured.")
        if sources and enabled_source_count == 0:
            missing_requirements.append("All configured external news sources are disabled.")
        if not self._settings.news_intelligence_sync_enabled:
            missing_requirements.append("External news sync is not enabled.")
        if self._settings.news_intelligence_mode == "live" and enabled_source_count == 0:
            missing_requirements.append(
                "Live mode requires at least one enabled official external source."
            )
        if enabled_source_count > 0 and healthy_source_count == 0:
            missing_requirements.append(
                "No enabled official external source has a fresh successful sync yet."
            )

        status = "ready"
        if missing_requirements:
            status = "blocked" if self._settings.news_intelligence_mode == "live" else "partial"

        freshness_status = "healthy"
        if enabled_source_count == 0:
            freshness_status = "unknown"
        elif healthy_source_count == 0:
            freshness_status = "stale"
        elif stale_source_count > 0:
            freshness_status = "mixed"

        return NewsImpactReadinessDTO(
            mode=self._settings.news_intelligence_mode,
            sync_enabled=self._settings.news_intelligence_sync_enabled,
            configured_source_count=len(sources),
            enabled_source_count=enabled_source_count,
            healthy_source_count=healthy_source_count,
            stale_source_count=stale_source_count,
            status=status,
            freshness_status=freshness_status,
            missing_requirements=missing_requirements,
            sources=sources,
        )

    async def _load_health_by_source(self) -> dict[tuple[str, str], dict[str, object]]:
        if self._repository is None:
            return {}

        rows = await self._repository.list_latest_source_health()
        return {(str(row["provider"]), str(row["source_url"])): row for row in rows}

    def _build_source_dto(
        self,
        *,
        provider: str,
        url: str,
        source_type: str,
        enabled: bool,
        health: dict[str, object] | None,
        now: datetime,
    ) -> NewsImpactSourceDTO:
        checked_at = cast("datetime | None", None if health is None else health.get("checked_at"))
        age_minutes: float | None = None
        freshness_status = "unknown"
        last_status: str | None = None
        fetched_count: int | None = None
        error_message: str | None = None

        if health is not None:
            last_status = str(health.get("status") or "unknown")
            fetched_count = int(cast("int | float | str", health.get("fetched_count") or 0))
            error_message = (
                None if health.get("error_message") is None else str(health["error_message"])
            )
            if checked_at is not None:
                age_minutes = round((now - checked_at).total_seconds() / 60.0, 2)

            if last_status == "ok" and age_minutes is not None and age_minutes <= 180:
                freshness_status = "healthy"
            elif enabled:
                freshness_status = "stale"

        return NewsImpactSourceDTO(
            provider=provider,
            url=url,
            source_type=source_type,
            enabled=enabled,
            last_status=last_status,
            freshness_status=freshness_status,
            age_minutes=age_minutes,
            fetched_count=fetched_count,
            error_message=error_message,
            checked_at=checked_at,
        )
