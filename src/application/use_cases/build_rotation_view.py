"""Application use case that prepares ecosystem rotation intelligence."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol, cast

from src.application.dtos.intelligence_dto import RotationCategoryDTO
from src.application.intelligence_taxonomy import (
    infer_categories,
    infer_registry_matches,
    titleize_token,
)


class RotationDashboardReader(Protocol):
    """Reader contract for ecosystem rotation intelligence inputs."""

    async def get_topic_rotation(self, *, days: int, limit: int) -> list[dict[str, object]]: ...

    async def get_top_repos(
        self,
        category: str | None,
        days: int,
        limit: int,
    ) -> list[dict[str, object]]: ...


def _as_int(value: object) -> int:
    return int(cast("int | float | str", value or 0))


def _as_float(value: object) -> float:
    return float(cast("int | float | str", value or 0.0))


def _clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return max(minimum, min(value, maximum))


class BuildRotationViewUseCase:
    """Build a frontend-ready ecosystem rotation list from dashboard analytics inputs."""

    def __init__(self, reader: RotationDashboardReader) -> None:
        self._reader = reader

    async def execute(self, *, days: int, limit: int) -> list[RotationCategoryDTO]:
        rows = await self._reader.get_topic_rotation(days=days, limit=limit)
        top_repos = await self._reader.get_top_repos(category=None, days=days, limit=50)

        results: list[RotationCategoryDTO] = []
        for row in rows:
            topic = str(row.get("topic") or "")
            topic_matches = [
                item
                for item in top_repos
                if topic and topic in cast("list[str]", item.get("topics") or [])
            ]
            matching_repos = [str(item.get("repo_full_name") or "") for item in topic_matches]
            registry_matches = infer_registry_matches(
                topic,
                *[str(item.get("description") or "") for item in topic_matches[:5]],
            )
            inferred_categories = infer_categories(
                topic,
                *[str(item.get("description") or "") for item in topic_matches[:5]],
            )
            current_attention_score = round(_as_float(row.get("current_star_count")), 2)
            previous_attention_score = round(_as_float(row.get("previous_star_count")), 2)
            attention_delta = round(_as_float(row.get("star_delta")), 2)
            confidence_score = round(
                _clamp(
                    45
                    + _as_int(row.get("repo_count")) * 2
                    + min(current_attention_score, 500) / 10
                    - max(previous_attention_score - current_attention_score, 0) / 20
                ),
                2,
            )
            rotation_drivers = [
                f"{_as_int(row.get('repo_count'))} repositories contributed to this shift.",
                f"Current attention score: {int(current_attention_score)}.",
                f"Previous attention score: {int(previous_attention_score)}.",
            ]
            if attention_delta != 0:
                rotation_drivers.append(f"Window-over-window change: {attention_delta:+.0f}.")
            if registry_matches:
                rotation_drivers.append(
                    "Registry evidence: "
                    + ", ".join(match.display_name for match in registry_matches[:3])
                    + "."
                )
            rotation_drivers.append(
                f"Mapped from topic token '{titleize_token(topic)}' into product taxonomy."
            )

            results.append(
                RotationCategoryDTO(
                    category=inferred_categories[0],
                    current_attention_score=current_attention_score,
                    previous_attention_score=previous_attention_score,
                    attention_delta=attention_delta,
                    repo_count=_as_int(row.get("repo_count")),
                    top_repos=matching_repos[:3],
                    top_topics=[titleize_token(topic)] if topic else [],
                    confidence_score=confidence_score,
                    rotation_drivers=rotation_drivers,
                    last_computed_at=datetime.now(tz=UTC),
                )
            )

        return results
