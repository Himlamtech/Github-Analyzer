"""Computed backend view for the framework radar page."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol, cast

from src.application.dtos.intelligence_dto import (
    FrameworkRadarItemDTO,
    FrameworkRadarSnapshotDTO,
    RadarWinnerDTO,
)
from src.application.intelligence_taxonomy import framework_registry


class FrameworkRadarDashboardReader(Protocol):
    """Dashboard inputs used to compute framework radar metrics."""

    async def get_top_repos(
        self,
        category: str | None,
        days: int,
        limit: int,
    ) -> list[dict[str, object]]: ...

    async def get_trending(self, days: int, limit: int) -> list[dict[str, object]]: ...


def _as_float(value: object) -> float:
    return float(cast("int | float | str", value or 0.0))


def _as_int(value: object) -> int:
    return int(cast("int | float | str", value or 0))


def _clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(value, maximum))


class GetFrameworkRadarSnapshotUseCase:
    """Build framework radar outputs from live repository analytics."""

    def __init__(self, reader: FrameworkRadarDashboardReader) -> None:
        self._reader = reader

    async def execute(self) -> FrameworkRadarSnapshotDTO:
        top_repos = await self._reader.get_top_repos(category=None, days=30, limit=80)
        trending = await self._reader.get_trending(days=30, limit=80)
        repo_pool = [*top_repos, *trending]

        frameworks: list[FrameworkRadarItemDTO] = []
        for definition in framework_registry():
            matched = [
                row
                for row in repo_pool
                if any(keyword in self._repo_haystack(row) for keyword in definition.keywords)
            ]
            if not matched:
                continue

            total_velocity = sum(_as_float(row.get("star_count_in_window")) for row in matched)
            total_stars = sum(_as_float(row.get("stargazers_count")) for row in matched)
            avg_issues = sum(_as_float(row.get("open_issues_count")) for row in matched) / len(
                matched
            )
            contributor_energy = min(
                100,
                round(total_velocity / max(len(matched), 1) / 4.0 + len(matched) * 12),
            )
            velocity_score = round(_clamp(total_velocity / 1200.0), 2)
            commercial_readiness = round(
                _clamp(total_stars / 250000.0 + 0.15 - avg_issues / 400.0), 2
            )
            frameworks.append(
                FrameworkRadarItemDTO(
                    framework_id=definition.framework_id,
                    framework_name=definition.framework_name,
                    velocity_score=velocity_score,
                    commercial_readiness_score=commercial_readiness,
                    contributor_energy_score=contributor_energy,
                    market_footprint=self._market_footprint(
                        total_stars=total_stars, repo_count=len(matched)
                    ),
                    strategic_insight_summary=self._insight_summary(
                        framework_name=definition.framework_name,
                        total_velocity=total_velocity,
                        repo_count=len(matched),
                        avg_issues=avg_issues,
                    ),
                )
            )

        frameworks.sort(
            key=lambda item: (
                item.velocity_score,
                item.commercial_readiness_score,
                item.contributor_energy_score,
            ),
            reverse=True,
        )
        winners = [
            RadarWinnerDTO(
                title=item.framework_name,
                summary=(
                    f"Velocity {item.velocity_score:.2f} with contributor energy "
                    f"{item.contributor_energy_score}."
                ),
            )
            for item in frameworks[:2]
        ]
        warnings = [
            RadarWinnerDTO(
                title=item.framework_name,
                summary=(
                    f"Commercial readiness {item.commercial_readiness_score:.2f} requires "
                    "continued ecosystem hardening."
                ),
            )
            for item in sorted(frameworks, key=lambda item: item.commercial_readiness_score)[:2]
        ]

        return FrameworkRadarSnapshotDTO(
            generated_at=datetime.now(tz=UTC),
            frameworks=frameworks,
            winners=winners,
            warnings=warnings,
        )

    @staticmethod
    def _repo_haystack(row: dict[str, object]) -> str:
        topics = " ".join(str(topic) for topic in cast("list[object]", row.get("topics") or []))
        return " ".join(
            [
                str(row.get("repo_full_name") or "").lower(),
                str(row.get("description") or "").lower(),
                topics.lower(),
            ]
        )

    @staticmethod
    def _market_footprint(*, total_stars: float, repo_count: int) -> str:
        if total_stars >= 150000 or repo_count >= 5:
            return "Enterprise Standard"
        if total_stars >= 50000 or repo_count >= 3:
            return "Expanding Ecosystem"
        return "Emerging & Experimental"

    @staticmethod
    def _insight_summary(
        *,
        framework_name: str,
        total_velocity: float,
        repo_count: int,
        avg_issues: float,
    ) -> str:
        return (
            f"{framework_name} is backed by {repo_count} matched repositories and "
            f"{round(total_velocity)} stars in the current analytics window. "
            f"Average open-issue pressure sits near {round(avg_issues)}."
        )
