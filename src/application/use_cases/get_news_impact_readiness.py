"""Readiness snapshot for external news-impact ingestion."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.application.dtos.intelligence_dto import (
    NewsImpactReadinessDTO,
    NewsImpactSourceDTO,
)

if TYPE_CHECKING:
    from src.infrastructure.config import Settings


class GetNewsImpactReadinessUseCase:
    """Describe whether NewsImpact can move beyond curated snapshots."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def execute(self) -> NewsImpactReadinessDTO:
        sources = [
            NewsImpactSourceDTO(
                provider=source.provider,
                url=str(source.url),
                source_type=source.source_type,
                enabled=source.enabled,
            )
            for source in self._settings.news_intelligence_sources
        ]
        enabled_source_count = sum(1 for source in sources if source.enabled)

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

        status = "ready"
        if missing_requirements:
            status = "blocked" if self._settings.news_intelligence_mode == "live" else "partial"

        return NewsImpactReadinessDTO(
            mode=self._settings.news_intelligence_mode,
            sync_enabled=self._settings.news_intelligence_sync_enabled,
            configured_source_count=len(sources),
            enabled_source_count=enabled_source_count,
            status=status,
            missing_requirements=missing_requirements,
            sources=sources,
        )
