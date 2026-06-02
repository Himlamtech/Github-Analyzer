"""Computed backend view for the framework radar page."""

from __future__ import annotations

from datetime import UTC, datetime
import re
from typing import Protocol, cast

from src.application.dtos.intelligence_dto import (
    FrameworkRadarItemDTO,
    FrameworkRadarSnapshotDTO,
    RadarWinnerDTO,
)
from src.application.intelligence_taxonomy import framework_registry, titleize_token


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


_GENERIC_TOPIC_TOKENS = {
    "ai",
    "agents",
    "agent",
    "agentic-ai",
    "awesome-list",
    "llm",
    "other",
    "python",
    "typescript",
    "javascript",
    "tooling",
    "framework",
    "free",
    "sdk",
}


class GetFrameworkRadarSnapshotUseCase:
    """Build framework radar outputs from live repository analytics."""

    def __init__(self, reader: FrameworkRadarDashboardReader) -> None:
        self._reader = reader

    async def execute(self) -> FrameworkRadarSnapshotDTO:
        top_repos = await self._reader.get_top_repos(category=None, days=30, limit=80)
        trending = await self._reader.get_trending(days=30, limit=80)
        repo_pool = list(
            {
                str(row.get("repo_full_name") or f"repo-{index}"): row
                for index, row in enumerate([*top_repos, *trending])
            }.values()
        )

        frameworks: list[FrameworkRadarItemDTO] = []
        for definition in framework_registry():
            matched = [
                row
                for row in repo_pool
                if any(keyword in self._repo_haystack(row) for keyword in definition.keywords)
            ]
            if not matched:
                continue

            frameworks.append(
                self._build_framework_item(
                    framework_id=definition.framework_id,
                    framework_name=definition.framework_name,
                    matched=matched,
                )
            )

        if not frameworks:
            frameworks = self._build_fallback_frameworks(repo_pool)

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

    def _build_fallback_frameworks(
        self, repo_pool: list[dict[str, object]]
    ) -> list[FrameworkRadarItemDTO]:
        grouped: dict[str, list[dict[str, object]]] = {}
        for row in repo_pool:
            label = self._fallback_label(row)
            grouped.setdefault(label, []).append(row)

        ranked_groups = sorted(
            grouped.items(),
            key=lambda item: sum(_as_float(row.get("star_count_in_window")) for row in item[1]),
            reverse=True,
        )
        return [
            self._build_framework_item(
                framework_id=self._slugify(label),
                framework_name=label,
                matched=rows,
            )
            for label, rows in ranked_groups[:5]
            if rows
        ]

    def _build_framework_item(
        self,
        *,
        framework_id: str,
        framework_name: str,
        matched: list[dict[str, object]],
    ) -> FrameworkRadarItemDTO:
        total_velocity = sum(_as_float(row.get("star_count_in_window")) for row in matched)
        total_stars = sum(_as_float(row.get("stargazers_count")) for row in matched)
        avg_issues = sum(_as_float(row.get("open_issues_count")) for row in matched) / len(matched)
        contributor_energy = min(
            100,
            round(total_velocity / max(len(matched), 1) / 4.0 + len(matched) * 12),
        )
        velocity_score = round(_clamp(total_velocity / 1200.0), 2)
        commercial_readiness = round(_clamp(total_stars / 250000.0 + 0.15 - avg_issues / 400.0), 2)
        return FrameworkRadarItemDTO(
            framework_id=framework_id,
            framework_name=framework_name,
            velocity_score=velocity_score,
            commercial_readiness_score=commercial_readiness,
            contributor_energy_score=contributor_energy,
            market_footprint=self._market_footprint(
                total_stars=total_stars,
                repo_count=len(matched),
            ),
            matched_repo_count=len(matched),
            representative_repos=[str(row.get("repo_full_name") or "") for row in matched[:3]],
            strategic_insight_summary=self._insight_summary(
                framework_name=framework_name,
                total_velocity=total_velocity,
                repo_count=len(matched),
                avg_issues=avg_issues,
            ),
        )

    @staticmethod
    def _fallback_label(row: dict[str, object]) -> str:
        topics = [str(topic).strip() for topic in cast("list[object]", row.get("topics") or [])]
        for topic in topics:
            normalized = topic.lower().strip()
            if normalized and normalized not in _GENERIC_TOPIC_TOKENS:
                return titleize_token(topic)

        category = str(row.get("category") or "").strip()
        if category and category.lower() != "other":
            return category

        repo_name = str(row.get("repo_name") or row.get("repo_full_name") or "Emerging Stack")
        repo_tail = repo_name.split("/")[-1]
        return titleize_token(repo_tail)

    @staticmethod
    def _slugify(value: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
        return f"ecosystem-{slug or 'other'}"

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
