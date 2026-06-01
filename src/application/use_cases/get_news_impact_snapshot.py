"""Computed backend view for the news impact page."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Protocol, cast

from src.application.dtos.intelligence_dto import NewsImpactCurvePointDTO, NewsImpactEventDTO
from src.application.intelligence_taxonomy import infer_categories, infer_linked_frameworks
from src.domain.exceptions import DashboardQueryError

if TYPE_CHECKING:
    from src.domain.repositories.external_news_repository import ExternalNewsRepositoryABC


class NewsImpactDashboardReader(Protocol):
    """Dashboard inputs used to estimate repository-level impact."""

    async def get_top_repos(
        self,
        category: str | None,
        days: int,
        limit: int,
    ) -> list[dict[str, object]]: ...

    async def get_trending(self, days: int, limit: int) -> list[dict[str, object]]: ...


def _clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return max(minimum, min(value, maximum))


def _as_float(value: object) -> float:
    return float(cast("int | float | str", value or 0.0))


def _score_repo_match(news_text: str, repo: dict[str, object], categories: list[str]) -> float:
    repo_name = str(repo.get("repo_full_name") or "")
    description = str(repo.get("description") or "")
    repo_category = str(repo.get("category") or "")
    topics = [str(topic) for topic in cast("list[object]", repo.get("topics") or [])]
    haystack = " ".join([repo_name.lower(), description.lower(), repo_category.lower(), *topics])

    score = 0.0
    for token in {part for part in news_text.split(" ") if len(part) >= 4}:
        if token in haystack:
            score += 1.0

    if repo_category and repo_category in categories:
        score += 2.0
    if any(category.lower() in haystack for category in categories):
        score += 1.5

    score += min(_as_float(repo.get("star_count_in_window")) / 300.0, 3.0)
    return score


class GetNewsImpactSnapshotUseCase:
    """Build NewsImpact items from persisted official external news data."""

    def __init__(
        self,
        repository: ExternalNewsRepositoryABC,
        reader: NewsImpactDashboardReader,
    ) -> None:
        self._repository = repository
        self._reader = reader

    async def execute(
        self,
        *,
        provider: str | None = None,
        limit: int = 20,
    ) -> list[NewsImpactEventDTO]:
        rows = await self._repository.list_latest_items(
            provider=provider,
            limit=limit,
            include_quarantined=False,
        )
        return await self._build_events(rows)

    async def get_detail(self, source_id: str) -> NewsImpactEventDTO | None:
        row = await self._repository.get_item_by_source_id(source_id)
        if row is None:
            return None
        events = await self._build_events([row])
        return events[0] if events else None

    async def _build_events(self, rows: list[dict[str, object]]) -> list[NewsImpactEventDTO]:
        if not rows:
            return []

        repo_pool, analytics_warning = await self._load_repo_pool()
        computed_at = datetime.now(tz=UTC)
        results: list[NewsImpactEventDTO] = []
        for row in rows:
            published_at = cast("datetime", row["published_at"])
            headline = str(row["title"])
            summary = str(row["summary"])
            provider = str(row["provider"])
            source_type = str(row.get("source_type") or "rss")
            event_type = str(row.get("event_type") or "news")
            categories = [
                str(item) for item in cast("list[object]", row.get("linked_categories") or [])
            ] or infer_categories(headline, summary)
            linked_repos = list(
                dict.fromkeys(
                    str(item)
                    for item in cast("list[object]", row.get("linked_repo_full_names") or [])
                )
            )
            linked_frameworks = list(
                dict.fromkeys(
                    str(item)
                    for item in cast("list[object]", row.get("linked_framework_ids") or [])
                )
            ) or infer_linked_frameworks(provider, headline, summary)
            news_text = f"{headline} {summary}".lower()
            ranked_repos = sorted(
                repo_pool,
                key=lambda repo: _score_repo_match(news_text, repo, categories),
                reverse=True,
            )
            matched_repos = list(
                dict.fromkeys(
                    [*linked_repos]
                    + [
                        str(repo.get("repo_full_name") or "")
                        for repo in ranked_repos
                        if _score_repo_match(news_text, repo, categories) > 1.0
                    ]
                )
            )[:3]
            repo_momentum = sum(
                _as_float(repo.get("star_count_in_window")) for repo in ranked_repos[:3]
            )
            age_hours = max((computed_at - published_at).total_seconds() / 3600.0, 0.0)
            causality_score = round(
                _clamp(
                    30.0
                    + float(len(matched_repos)) * 12.0
                    + float(len(categories)) * 7.0
                    + min(repo_momentum / 25.0, 28.0)
                    + _as_float(row.get("quality_score")) / 5.0
                    - min(age_hours / 18.0, 15.0)
                ),
                2,
            )
            lag_hours = round(
                max(1.0, 36.0 - float(len(matched_repos)) * 4.0 - min(repo_momentum / 60.0, 18.0)),
                2,
            )
            impact_curve = self._build_curve(
                repo_momentum=repo_momentum, causality_score=causality_score
            )
            explanation_trace = [
                f"Computed from persisted official {provider} source item.",
                (
                    f"Matched {len(matched_repos)} repositories against current "
                    "GitHub analytics windows."
                ),
                f"Categories inferred for this event: {', '.join(categories)}.",
            ]
            if linked_frameworks:
                explanation_trace.append(
                    f"Registry-linked frameworks: {', '.join(linked_frameworks)}."
                )
            if row.get("quality_score") is not None:
                explanation_trace.append(
                    f"Source content quality score: {round(_as_float(row['quality_score']), 1)}."
                )
            if analytics_warning is not None:
                explanation_trace.append(analytics_warning)

            results.append(
                NewsImpactEventDTO(
                    event_id=str(row["source_id"]),
                    source="persisted_external_news",
                    headline=headline,
                    published_at=published_at,
                    provider=provider,
                    event_type=event_type,
                    linked_entities=[
                        str(item)
                        for item in cast("list[object]", row.get("linked_entities") or [])
                    ],
                    linked_categories=categories,
                    linked_repos=linked_repos,
                    linked_frameworks=linked_frameworks,
                    quality_score=round(_as_float(row.get("quality_score")), 2),
                    source_type=source_type,
                    causality_score=causality_score,
                    lag_hours=lag_hours,
                    impact_summary=self._build_summary(
                        categories=categories,
                        matched_repos=matched_repos,
                        causality_score=causality_score,
                    ),
                    impact_curve=impact_curve,
                    top_impacted_repos=matched_repos,
                    is_quarantined=bool(row.get("is_quarantined") or False),
                    quarantine_reason=(
                        None
                        if row.get("quarantine_reason") is None
                        else str(row.get("quarantine_reason"))
                    ),
                    explanation_trace=explanation_trace,
                    last_computed_at=computed_at,
                )
            )

        return results

    async def _load_repo_pool(self) -> tuple[list[dict[str, object]], str | None]:
        try:
            top_repos = await self._reader.get_top_repos(category=None, days=30, limit=80)
            trending = await self._reader.get_trending(days=30, limit=40)
        except DashboardQueryError as exc:
            return [], f"GitHub telemetry matching is temporarily degraded: {exc.message}"

        return [*top_repos, *trending], None

    def _build_curve(
        self,
        *,
        repo_momentum: float,
        causality_score: float,
    ) -> list[NewsImpactCurvePointDTO]:
        base = max(8.0, repo_momentum / 20.0 + causality_score / 8.0)
        multipliers = [0.2, 0.35, 0.55, 0.75, 1.0, 1.18]
        buckets = ["0h", "2h", "6h", "12h", "24h", "48h"]
        return [
            NewsImpactCurvePointDTO(time_bucket=bucket, value=max(1, round(base * factor)))
            for bucket, factor in zip(buckets, multipliers, strict=True)
        ]

    @staticmethod
    def _build_summary(
        *,
        categories: list[str],
        matched_repos: list[str],
        causality_score: float,
    ) -> str:
        lead_category = categories[0] if categories else "Developer Tooling"
        repo_count = len(matched_repos)
        return (
            f"{lead_category} moved first, with {repo_count} matched repos and a computed "
            f"causality score of {causality_score:.0f}."
        )
