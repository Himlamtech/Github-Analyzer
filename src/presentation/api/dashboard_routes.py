"""Dashboard API endpoints — analytical queries for the visualization dashboard.

All endpoints:
- Depend on ClickHouseDashboardService via ``_get_dashboard_service()`` factory.
- Return frozen Pydantic DTOs from ``src.application.dtos.repo_metadata_dto``.
- Raise HTTPException(503) on DashboardQueryError.
- Use structlog for structured error logging.

Router prefix: /dashboard
Tags: ["Dashboard"]
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Annotated, cast

from fastapi import APIRouter, Depends, HTTPException, Query
import structlog

from src.application.dtos.repo_metadata_dto import (
    CategorySummaryDTO,
    LanguageBreakdownDTO,
    NewsHeadlineDTO,
    NewsRadarResponseDTO,
    RepoMetadataDTO,
    RepoNewsRadarDTO,
    RepoTimeseriesPointDTO,
    ShockMoverDTO,
    ShockMoversResponseDTO,
    TopicBreakdownDTO,
    TopicRotationDTO,
    TopRepoDTO,
    TrendingRepoDTO,
)
from src.domain.exceptions import DashboardQueryError
from src.infrastructure.config import Settings, get_settings

if TYPE_CHECKING:
    from src.infrastructure.news.searxng_news_service import SearXNGNewsService
    from src.infrastructure.storage.clickhouse_dashboard_service import (
        ClickHouseDashboardService,
    )

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


# ── Dependency factory ────────────────────────────────────────────────────────


def _get_dashboard_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> object:
    """Construct a ClickHouseDashboardService for the request."""
    from src.infrastructure.storage.clickhouse_dashboard_service import (
        ClickHouseDashboardService,
    )

    return ClickHouseDashboardService(
        host=settings.clickhouse_host,
        port=settings.clickhouse_port,
        user=settings.clickhouse_user,
        password=settings.clickhouse_password,
        database=settings.clickhouse_database,
        parquet_base_path=settings.parquet_base_path,
    )


def _get_news_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> object:
    """Construct the SearXNG-backed news service for the request."""
    from src.infrastructure.news.searxng_news_service import SearXNGNewsService

    return SearXNGNewsService(
        base_url=str(settings.searxng_base_url),
        timeout_seconds=settings.searxng_timeout_seconds,
        headline_limit=settings.searxng_news_limit,
    )


# ── Helpers ───────────────────────────────────────────────────────────────────


def _ensure_utc(value: object) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    return datetime.now(tz=UTC)


def _as_string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _as_int(value: object) -> int:
    return int(cast("int | float | str", value or 0))


def _as_float(value: object) -> float:
    return float(cast("int | float | str", value or 0.0))


def _to_repo_dto(raw: dict[str, object]) -> RepoMetadataDTO:
    """Map a raw ClickHouse result dict to a RepoMetadataDTO.

    Args:
        raw: Dict from ClickHouseDashboardService query methods.

    Returns:
        Fully populated RepoMetadataDTO.
    """

    return RepoMetadataDTO(
        repo_id=_as_int(raw.get("repo_id")),
        repo_full_name=str(raw.get("repo_full_name") or ""),
        repo_name=str(raw.get("repo_name") or ""),
        html_url=str(raw.get("html_url") or ""),
        description=str(raw.get("description") or ""),
        primary_language=str(raw.get("primary_language") or ""),
        topics=_as_string_list(raw.get("topics")),
        category=str(raw.get("category") or "Other"),
        stargazers_count=_as_int(raw.get("stargazers_count")),
        watchers_count=_as_int(raw.get("watchers_count")),
        forks_count=_as_int(raw.get("forks_count")),
        open_issues_count=_as_int(raw.get("open_issues_count")),
        subscribers_count=_as_int(raw.get("subscribers_count")),
        owner_login=str(raw.get("owner_login") or ""),
        owner_avatar_url=str(raw.get("owner_avatar_url") or ""),
        license_name=str(raw.get("license_name") or ""),
        github_created_at=_ensure_utc(raw.get("github_created_at")),
        github_pushed_at=_ensure_utc(raw.get("github_pushed_at")),
        rank=_as_int(raw.get("rank")),
    )


def _to_shock_mover_dto(raw: dict[str, object]) -> ShockMoverDTO:
    """Map a raw mover row to the public shock-mover DTO."""
    return ShockMoverDTO(
        repo=_to_repo_dto(raw),
        star_count_in_window=_as_int(raw.get("star_count_in_window")),
        previous_star_count_in_window=_as_int(raw.get("previous_star_count_in_window")),
        unique_actors_in_window=_as_int(raw.get("unique_actors_in_window")),
        weekly_percent_gain=_as_float(raw.get("weekly_percent_gain")),
        window_over_window_ratio=_as_float(raw.get("window_over_window_ratio")),
        rank=_as_int(raw.get("rank")),
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("/top-repos", response_model=list[TopRepoDTO])
async def get_top_repos(
    svc: Annotated[object, Depends(_get_dashboard_service)],
    category: Annotated[
        str | None,
        Query(description="Category filter: LLM, Agent, Diffusion, Multimodal, DataEng, Other"),
    ] = None,
    days: Annotated[int, Query(ge=1, le=90)] = 7,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[TopRepoDTO]:
    """Top AI repos by star activity in the look-back window.

    Args:
        category: Optional category filter. Returns all categories if omitted.
        days:     Look-back window in days (1-90).
        limit:    Maximum repos to return (1-100).
    """
    service = cast("ClickHouseDashboardService", svc)

    try:
        rows = await service.get_top_repos(category=category, days=days, limit=limit)
    except DashboardQueryError as exc:
        logger.error("dashboard.top_repos_failed", category=category, error=str(exc))
        raise HTTPException(status_code=503, detail="Dashboard query failed") from exc

    return [
        TopRepoDTO(
            repo=_to_repo_dto(row),
            star_count_in_window=int(row.get("star_count_in_window") or 0),
            star_delta=0,
        )
        for row in rows
    ]


@router.get("/top-starred-repos", response_model=list[TopRepoDTO])
async def get_top_starred_repos(
    svc: Annotated[object, Depends(_get_dashboard_service)],
    category: Annotated[
        str | None,
        Query(description="Category filter: LLM, Agent, Diffusion, Multimodal, DataEng, Other"),
    ] = None,
    days: Annotated[int, Query(ge=1, le=365)] = 7,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[TopRepoDTO]:
    """Top AI repos by all-time current total star count."""
    service = cast("ClickHouseDashboardService", svc)

    try:
        rows = await service.get_top_starred_repos(category=category, limit=limit, days=days)
    except DashboardQueryError as exc:
        logger.error("dashboard.top_starred_repos_failed", category=category, error=str(exc))
        raise HTTPException(status_code=503, detail="Dashboard query failed") from exc

    return [
        TopRepoDTO(
            repo=_to_repo_dto(row),
            star_count_in_window=int(row.get("star_count_in_window") or 0),
            star_delta=0,
        )
        for row in rows
    ]


@router.get("/trending", response_model=list[TrendingRepoDTO])
async def get_trending(
    svc: Annotated[object, Depends(_get_dashboard_service)],
    days: Annotated[int, Query(ge=1, le=90)] = 7,
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
) -> list[TrendingRepoDTO]:
    """Top repos gaining the most stars in the current GMT+7 week.

    Args:
        days:  Accepted for backward compatibility; the ranking uses the current GMT+7 week.
        limit: Maximum repos to return (1-100).
    """
    service = cast("ClickHouseDashboardService", svc)

    try:
        rows = await service.get_trending(days=days, limit=limit)
    except DashboardQueryError as exc:
        logger.error("dashboard.trending_failed", error=str(exc))
        raise HTTPException(status_code=503, detail="Dashboard query failed") from exc

    return [
        TrendingRepoDTO(
            repo=_to_repo_dto(row),
            star_count_in_window=int(row.get("star_count_in_window") or 0),
            growth_rank=int(row.get("growth_rank") or idx + 1),
        )
        for idx, row in enumerate(rows)
    ]


@router.get("/shock-movers", response_model=ShockMoversResponseDTO)
async def get_shock_movers(
    svc: Annotated[object, Depends(_get_dashboard_service)],
    days: Annotated[int, Query(ge=1, le=90)] = 7,
    absolute_limit: Annotated[int, Query(ge=1, le=12)] = 6,
    percentage_limit: Annotated[int, Query(ge=1, le=12)] = 6,
    min_baseline_stars: Annotated[int, Query(ge=100, le=2_000_000)] = 1_000,
) -> ShockMoversResponseDTO:
    """Return the strongest absolute and percentage movers for the selected window."""
    service = cast("ClickHouseDashboardService", svc)

    try:
        payload = await service.get_shock_movers(
            days=days,
            absolute_limit=absolute_limit,
            percentage_limit=percentage_limit,
            min_baseline_stars=min_baseline_stars,
        )
    except DashboardQueryError as exc:
        logger.error("dashboard.shock_movers_failed", error=str(exc), days=days)
        raise HTTPException(status_code=503, detail="Dashboard query failed") from exc

    return ShockMoversResponseDTO(
        window_days=days,
        absolute_movers=[
            _to_shock_mover_dto(item)
            for item in cast("list[dict[str, object]]", payload["absolute_movers"])
        ],
        percentage_movers=[
            _to_shock_mover_dto(item)
            for item in cast("list[dict[str, object]]", payload["percentage_movers"])
        ],
    )


@router.get("/topic-rotation", response_model=list[TopicRotationDTO])
async def get_topic_rotation(
    svc: Annotated[object, Depends(_get_dashboard_service)],
    days: Annotated[int, Query(ge=1, le=90)] = 7,
    limit: Annotated[int, Query(ge=1, le=20)] = 8,
) -> list[TopicRotationDTO]:
    """Return the topics accelerating fastest versus the prior matching window."""
    service = cast("ClickHouseDashboardService", svc)

    try:
        rows = await service.get_topic_rotation(days=days, limit=limit)
    except DashboardQueryError as exc:
        logger.error("dashboard.topic_rotation_failed", error=str(exc), days=days)
        raise HTTPException(status_code=503, detail="Dashboard query failed") from exc

    return [
        TopicRotationDTO(
            topic=str(row.get("topic") or ""),
            current_star_count=int(row.get("current_star_count") or 0),
            previous_star_count=int(row.get("previous_star_count") or 0),
            star_delta=int(row.get("star_delta") or 0),
            repo_count=int(row.get("repo_count") or 0),
            rank=int(row.get("rank") or idx + 1),
        )
        for idx, row in enumerate(rows)
    ]


@router.get("/news-radar", response_model=NewsRadarResponseDTO)
async def get_news_radar(
    svc: Annotated[object, Depends(_get_dashboard_service)],
    news_svc: Annotated[object, Depends(_get_news_service)],
    days: Annotated[int, Query(ge=1, le=90)] = 7,
    repo_limit: Annotated[int, Query(ge=1, le=8)] = 4,
    min_baseline_stars: Annotated[int, Query(ge=100, le=2_000_000)] = 1_000,
    focus: Annotated[str, Query(pattern="^(absolute|percentage)$")] = "percentage",
) -> NewsRadarResponseDTO:
    """Return external headlines for the current breakout repositories."""
    dashboard_service = cast("ClickHouseDashboardService", svc)
    news_service = cast("SearXNGNewsService", news_svc)

    try:
        movers = await dashboard_service.get_shock_movers(
            days=days,
            absolute_limit=repo_limit,
            percentage_limit=repo_limit,
            min_baseline_stars=min_baseline_stars,
        )
        selected_rows = cast(
            "list[dict[str, object]]",
            movers["percentage_movers" if focus == "percentage" else "absolute_movers"],
        )
        headlines_per_repo = await asyncio.gather(
            *[
                news_service.search_repo_news(
                    repo_full_name=str(row.get("repo_full_name") or ""),
                    days=days,
                )
                for row in selected_rows
            ]
        )
    except DashboardQueryError as exc:
        logger.warning("dashboard.news_radar_unavailable", error=str(exc), days=days, focus=focus)
        return NewsRadarResponseDTO(window_days=days, repos=[])

    repos: list[RepoNewsRadarDTO] = []
    for row, headlines in zip(selected_rows, headlines_per_repo, strict=True):
        repos.append(
            RepoNewsRadarDTO(
                repo_full_name=str(row.get("repo_full_name") or ""),
                category=str(row.get("category") or "Other"),
                star_count_in_window=int(
                    cast("int | float | str", row.get("star_count_in_window") or 0)
                ),
                weekly_percent_gain=float(
                    cast("int | float | str", row.get("weekly_percent_gain") or 0.0)
                ),
                headlines=[
                    NewsHeadlineDTO(
                        title=str(item.get("title") or ""),
                        url=str(item.get("url") or ""),
                        source=str(item.get("source") or "web"),
                        snippet=str(item.get("snippet") or ""),
                        engine=str(item.get("engine")) if item.get("engine") is not None else None,
                    )
                    for item in headlines
                    if str(item.get("title") or "").strip() and str(item.get("url") or "").strip()
                ],
            )
        )

    return NewsRadarResponseDTO(window_days=days, repos=repos)


@router.get("/topic-breakdown", response_model=list[TopicBreakdownDTO])
async def get_topic_breakdown(
    svc: Annotated[object, Depends(_get_dashboard_service)],
    days: Annotated[int, Query(ge=1, le=90)] = 7,
) -> list[TopicBreakdownDTO]:
    """Star counts grouped by GitHub topic tag (top 30).

    Args:
        days: Look-back window in days (1-90).
    """
    service = cast("ClickHouseDashboardService", svc)

    try:
        rows = await service.get_topic_breakdown(days=days)
    except DashboardQueryError as exc:
        logger.error("dashboard.topic_breakdown_failed", error=str(exc))
        raise HTTPException(status_code=503, detail="Dashboard query failed") from exc

    return [
        TopicBreakdownDTO(
            topic=str(row.get("topic") or ""),
            event_count=int(row.get("event_count") or 0),
            repo_count=int(row.get("repo_count") or 0),
        )
        for row in rows
    ]


@router.get("/language-breakdown", response_model=list[LanguageBreakdownDTO])
async def get_language_breakdown(
    svc: Annotated[object, Depends(_get_dashboard_service)],
    days: Annotated[int, Query(ge=1, le=90)] = 7,
) -> list[LanguageBreakdownDTO]:
    """Star counts grouped by primary programming language (top 20).

    Args:
        days: Look-back window in days (1-90).
    """
    service = cast("ClickHouseDashboardService", svc)

    try:
        rows = await service.get_language_breakdown(days=days)
    except DashboardQueryError as exc:
        logger.error("dashboard.language_breakdown_failed", error=str(exc))
        raise HTTPException(status_code=503, detail="Dashboard query failed") from exc

    return [
        LanguageBreakdownDTO(
            language=str(row.get("language") or ""),
            event_count=int(row.get("event_count") or 0),
            repo_count=int(row.get("repo_count") or 0),
        )
        for row in rows
    ]


@router.get("/repo-timeseries", response_model=list[RepoTimeseriesPointDTO])
async def get_repo_timeseries(
    svc: Annotated[object, Depends(_get_dashboard_service)],
    repo_name: Annotated[
        str,
        Query(
            min_length=3, pattern=r"^[^/]+/[^/]+$", description="Repository in owner/repo format"
        ),
    ],
    days: Annotated[int, Query(ge=1, le=365)] = 30,
) -> list[RepoTimeseriesPointDTO]:
    """Daily star count + total event count for a specific repository.

    Args:
        repo_name: Repository in ``owner/repo`` format.
        days:      Look-back window in days (1-365).
    """
    service = cast("ClickHouseDashboardService", svc)

    try:
        rows = await service.get_repo_timeseries(repo_name=repo_name, days=days)
    except DashboardQueryError as exc:
        logger.error("dashboard.repo_timeseries_failed", repo=repo_name, error=str(exc))
        raise HTTPException(status_code=503, detail="Dashboard query failed") from exc

    return [
        RepoTimeseriesPointDTO(
            event_date=row["event_date"],
            star_count=int(row.get("star_count") or 0),
            total_events=int(row.get("total_events") or 0),
        )
        for row in rows
    ]


@router.get("/category-summary", response_model=list[CategorySummaryDTO])
async def get_category_summary(
    svc: Annotated[object, Depends(_get_dashboard_service)],
) -> list[CategorySummaryDTO]:
    """Per-category aggregate stats: repo count, total stars, top repo, weekly delta."""
    service = cast("ClickHouseDashboardService", svc)

    try:
        rows = await service.get_category_summary()
    except DashboardQueryError as exc:
        logger.error("dashboard.category_summary_failed", error=str(exc))
        raise HTTPException(status_code=503, detail="Dashboard query failed") from exc

    return [
        CategorySummaryDTO(
            category=str(row.get("category") or ""),
            repo_count=int(row.get("repo_count") or 0),
            total_stars=int(row.get("total_stars") or 0),
            top_repo_name=str(row.get("top_repo_name") or ""),
            top_repo_stars=int(row.get("top_repo_stars") or 0),
            weekly_star_delta=int(row.get("weekly_star_delta") or 0),
        )
        for row in rows
    ]
