"""Application use case that prepares breakout intelligence for the frontend."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol, cast

from src.application.dtos.intelligence_dto import BreakoutRepositoryDTO
from src.application.dtos.repo_metadata_dto import RepoMetadataDTO


class BreakoutDashboardReader(Protocol):
    """Reader contract for breakout intelligence inputs."""

    async def get_top_repos(
        self,
        category: str | None,
        days: int,
        limit: int,
    ) -> list[dict[str, object]]: ...

    async def get_shock_movers(
        self,
        *,
        days: int,
        absolute_limit: int,
        percentage_limit: int,
        min_baseline_stars: int,
    ) -> dict[str, object]: ...


def _as_int(value: object) -> int:
    return int(cast("int | float | str", value or 0))


def _as_float(value: object) -> float:
    return float(cast("int | float | str", value or 0.0))


def _clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return max(minimum, min(value, maximum))


def _to_repo_dto(raw: dict[str, object]) -> RepoMetadataDTO:
    timestamp_now = datetime.now(tz=UTC)
    created_at = raw.get("github_created_at")
    pushed_at = raw.get("github_pushed_at")

    return RepoMetadataDTO(
        repo_id=_as_int(raw.get("repo_id")),
        repo_full_name=str(raw.get("repo_full_name") or ""),
        repo_name=str(raw.get("repo_name") or ""),
        html_url=str(raw.get("html_url") or ""),
        description=str(raw.get("description") or ""),
        primary_language=str(raw.get("primary_language") or ""),
        topics=[str(item) for item in cast("list[object]", raw.get("topics") or [])],
        category=str(raw.get("category") or "Other"),
        stargazers_count=_as_int(raw.get("stargazers_count")),
        watchers_count=_as_int(raw.get("watchers_count")),
        forks_count=_as_int(raw.get("forks_count")),
        open_issues_count=_as_int(raw.get("open_issues_count")),
        subscribers_count=_as_int(raw.get("subscribers_count")),
        owner_login=str(raw.get("owner_login") or ""),
        owner_avatar_url=str(raw.get("owner_avatar_url") or ""),
        license_name=str(raw.get("license_name") or ""),
        github_created_at=created_at if isinstance(created_at, datetime) else timestamp_now,
        github_pushed_at=pushed_at if isinstance(pushed_at, datetime) else timestamp_now,
        rank=_as_int(raw.get("rank")),
    )


class BuildBreakoutViewUseCase:
    """Build a frontend-ready breakout intelligence list from dashboard analytics inputs."""

    def __init__(self, reader: BreakoutDashboardReader) -> None:
        self._reader = reader

    async def execute(
        self,
        *,
        days: int,
        limit: int,
        category: str | None = None,
    ) -> list[BreakoutRepositoryDTO]:
        mover_payload = await self._reader.get_shock_movers(
            days=days,
            absolute_limit=limit,
            percentage_limit=limit,
            min_baseline_stars=1_000,
        )
        top_rows = await self._reader.get_top_repos(category=category, days=days, limit=limit)

        mover_index: dict[str, dict[str, object]] = {}
        for key in ("absolute_movers", "percentage_movers"):
            for item in cast("list[dict[str, object]]", mover_payload.get(key) or []):
                mover_index[str(item.get("repo_full_name") or "")] = item

        results: list[BreakoutRepositoryDTO] = []
        for row in top_rows:
            full_name = str(row.get("repo_full_name") or "")
            mover_data = mover_index.get(full_name, {})

            star_gain_7d = _as_int(row.get("star_count_in_window"))
            previous_window_gain = _as_int(mover_data.get("previous_star_count_in_window"))
            unique_actors_7d = _as_int(mover_data.get("unique_actors_in_window"))
            event_count_7d = max(star_gain_7d, unique_actors_7d)
            weekly_percent_gain = _as_float(mover_data.get("weekly_percent_gain"))
            window_ratio = _as_float(mover_data.get("window_over_window_ratio"))
            repo = _to_repo_dto(row)

            breakout_score = round(
                _clamp(star_gain_7d / 20 + window_ratio * 12 + unique_actors_7d / 5),
                2,
            )
            durability_score = round(
                _clamp(
                    (
                        repo.watchers_count
                        + repo.forks_count
                        + repo.subscribers_count * 2
                        + unique_actors_7d * 3
                    )
                    / max(repo.stargazers_count, 1)
                    * 1000
                ),
                2,
            )
            hype_risk_score = round(
                _clamp(
                    weekly_percent_gain * 1.5
                    - unique_actors_7d / 3
                    + max(1500 - repo.stargazers_count, 0) / 75
                ),
                2,
            )
            confidence_score = round(
                _clamp(
                    40
                    + unique_actors_7d / 4
                    + min(repo.stargazers_count, 20_000) / 800
                    - hype_risk_score / 3
                ),
                2,
            )

            explanation_trace = [
                f"Star gain in last {days}d: +{star_gain_7d}",
                f"Unique actors in last {days}d: {unique_actors_7d}",
                f"Window-over-window ratio: {window_ratio:.2f}",
            ]
            if previous_window_gain > 0:
                explanation_trace.append(
                    f"Star gain versus previous window: {star_gain_7d - previous_window_gain:+d}"
                )

            results.append(
                BreakoutRepositoryDTO(
                    repo=repo,
                    breakout_score=breakout_score,
                    durability_score=durability_score,
                    hype_risk_score=hype_risk_score,
                    confidence_score=confidence_score,
                    star_gain_7d=star_gain_7d,
                    unique_actors_7d=unique_actors_7d,
                    event_count_7d=event_count_7d,
                    star_gain_vs_previous_window=star_gain_7d - previous_window_gain,
                    explanation_trace=explanation_trace,
                    last_computed_at=datetime.now(tz=UTC),
                )
            )

        return sorted(results, key=lambda item: item.breakout_score, reverse=True)[:limit]
