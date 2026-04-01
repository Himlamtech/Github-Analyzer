"""Dashboard endpoints for repository analytics and market storytelling."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime
from typing import Annotated, cast

from fastapi import APIRouter, Depends, HTTPException, Query

from src.application.dtos.dashboard_dto import (
    CategorySummaryDTO,
    LanguageBreakdownDTO,
    ShockMoverDTO,
    ShockMoversResponseDTO,
    TimeseriesPointDTO,
    TopicBreakdownDTO,
    TopicRotationDTO,
    TopRepoResponseDTO,
    TrendingRepoResponseDTO,
)
from src.application.dtos.repo_metadata_dto import RepoMetadataDTO
from src.domain.exceptions import DashboardQueryError, ValidationError
from src.infrastructure.config import Settings, get_settings
from src.infrastructure.storage.clickhouse_dashboard_service import ClickHouseDashboardService

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])
DashboardRow = Mapping[str, object]


def _get_dashboard_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> ClickHouseDashboardService:
    """Construct the dashboard query service for the current request."""

    return ClickHouseDashboardService(
        host=settings.clickhouse_host,
        port=settings.clickhouse_port,
        user=settings.clickhouse_user,
        password=settings.clickhouse_password,
        database=settings.clickhouse_database,
        parquet_base_path=settings.parquet_base_path,
    )


@router.get("/top-repos", response_model=list[TopRepoResponseDTO])
async def get_top_repos(
    service: Annotated[ClickHouseDashboardService, Depends(_get_dashboard_service)],
    days: Annotated[int, Query(ge=1, le=365)] = 7,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    category: Annotated[str | None, Query()] = None,
) -> list[TopRepoResponseDTO]:
    """Return top repositories ranked by total stars with current-window lift."""

    try:
        rows = await service.get_top_repos(category=category, days=days, limit=limit)
        return [
            TopRepoResponseDTO(
                repo=_to_repo_metadata(row),
                star_count_in_window=_int_value(row.get("star_count_in_window")),
                star_delta=_int_value(row.get("star_delta")),
            )
            for row in rows
        ]
    except (DashboardQueryError, ValidationError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/trending", response_model=list[TrendingRepoResponseDTO])
async def get_trending_repositories(
    service: Annotated[ClickHouseDashboardService, Depends(_get_dashboard_service)],
    days: Annotated[int, Query(ge=1, le=365)] = 7,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> list[TrendingRepoResponseDTO]:
    """Return repositories leading the current momentum window."""

    try:
        rows = await service.get_trending(days=days, limit=limit)
        return [
            TrendingRepoResponseDTO(
                repo=_to_repo_metadata(row),
                star_count_in_window=_int_value(row.get("star_count_in_window")),
                growth_rank=_int_value(row.get("growth_rank")),
            )
            for row in rows
        ]
    except DashboardQueryError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/language-breakdown", response_model=list[LanguageBreakdownDTO])
async def get_language_breakdown(
    service: Annotated[ClickHouseDashboardService, Depends(_get_dashboard_service)],
    days: Annotated[int, Query(ge=1, le=365)] = 7,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> list[LanguageBreakdownDTO]:
    """Return star activity by language."""

    try:
        rows = await service.get_language_breakdown(days=days, limit=limit)
        return [_to_language_breakdown(row) for row in rows]
    except DashboardQueryError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/topic-breakdown", response_model=list[TopicBreakdownDTO])
async def get_topic_breakdown(
    service: Annotated[ClickHouseDashboardService, Depends(_get_dashboard_service)],
    days: Annotated[int, Query(ge=1, le=365)] = 7,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> list[TopicBreakdownDTO]:
    """Return star activity by topic."""

    try:
        rows = await service.get_topic_breakdown(days=days, limit=limit)
        return [_to_topic_breakdown(row) for row in rows]
    except DashboardQueryError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/repo-timeseries", response_model=list[TimeseriesPointDTO])
async def get_repo_timeseries(
    service: Annotated[ClickHouseDashboardService, Depends(_get_dashboard_service)],
    repo_name: Annotated[
        str,
        Query(
            min_length=3,
            pattern=r"^[^/]+/[^/]+$",
            description="Repository in owner/repo format",
        ),
    ],
    days: Annotated[int, Query(ge=1, le=365)] = 30,
) -> list[TimeseriesPointDTO]:
    """Return daily repository star/event activity."""

    try:
        rows = await service.get_repo_timeseries(repo_name=repo_name, days=days)
        return [_to_timeseries_point(row) for row in rows]
    except DashboardQueryError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/category-summary", response_model=list[CategorySummaryDTO])
async def get_category_summary(
    service: Annotated[ClickHouseDashboardService, Depends(_get_dashboard_service)],
    days: Annotated[int, Query(ge=1, le=365)] = 7,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> list[CategorySummaryDTO]:
    """Return ranked market categories for the selected window."""

    try:
        rows = await service.get_category_summary(days=days, limit=limit)
        return [_to_category_summary(row) for row in rows]
    except DashboardQueryError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/shock-movers", response_model=ShockMoversResponseDTO)
async def get_shock_movers(
    service: Annotated[ClickHouseDashboardService, Depends(_get_dashboard_service)],
    days: Annotated[int, Query(ge=1, le=365)] = 7,
    absolute_limit: Annotated[int, Query(ge=1, le=50)] = 20,
    percentage_limit: Annotated[int, Query(ge=1, le=50)] = 20,
    min_baseline_stars: Annotated[int, Query(ge=0, le=2_000_000)] = 1_000,
) -> ShockMoversResponseDTO:
    """Return the most notable weekly repository movers."""

    try:
        payload = await service.get_shock_movers(
            days=days,
            absolute_limit=absolute_limit,
            percentage_limit=percentage_limit,
            min_baseline_stars=min_baseline_stars,
        )
        return ShockMoversResponseDTO(
            window_days=_int_value(payload.get("window_days")),
            absolute_movers=[
                ShockMoverDTO(
                    repo=_to_repo_metadata(item),
                    star_count_in_window=_int_value(item.get("star_count_in_window")),
                    previous_star_count_in_window=_int_value(
                        item.get("previous_star_count_in_window")
                    ),
                    unique_actors_in_window=_int_value(item.get("unique_actors_in_window")),
                    weekly_percent_gain=_float_value(item.get("weekly_percent_gain")),
                    window_over_window_ratio=_float_value(item.get("window_over_window_ratio")),
                    rank=_int_value(item.get("rank")),
                )
                for item in cast("list[DashboardRow]", payload.get("absolute_movers", []))
            ],
            percentage_movers=[
                ShockMoverDTO(
                    repo=_to_repo_metadata(item),
                    star_count_in_window=_int_value(item.get("star_count_in_window")),
                    previous_star_count_in_window=_int_value(
                        item.get("previous_star_count_in_window")
                    ),
                    unique_actors_in_window=_int_value(item.get("unique_actors_in_window")),
                    weekly_percent_gain=_float_value(item.get("weekly_percent_gain")),
                    window_over_window_ratio=_float_value(item.get("window_over_window_ratio")),
                    rank=_int_value(item.get("rank")),
                )
                for item in cast("list[DashboardRow]", payload.get("percentage_movers", []))
            ],
        )
    except DashboardQueryError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/topic-rotation", response_model=list[TopicRotationDTO])
async def get_topic_rotation(
    service: Annotated[ClickHouseDashboardService, Depends(_get_dashboard_service)],
    days: Annotated[int, Query(ge=1, le=365)] = 7,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> list[TopicRotationDTO]:
    """Return topics gaining star activity versus the prior window."""

    try:
        rows = await service.get_topic_rotation(days=days, limit=limit)
        return [_to_topic_rotation(row) for row in rows]
    except DashboardQueryError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def _to_repo_metadata(data: DashboardRow) -> RepoMetadataDTO:
    return RepoMetadataDTO(
        repo_id=_int_value(data.get("repo_id")),
        repo_full_name=str(data["repo_full_name"]),
        repo_name=str(data["repo_name"]),
        html_url=str(data["html_url"]),
        description=str(data.get("description") or ""),
        primary_language=str(data.get("primary_language") or ""),
        topics=_string_list(data.get("topics")),
        category=str(data.get("category") or "Other"),
        stargazers_count=_int_value(data.get("stargazers_count")),
        watchers_count=_int_value(data.get("watchers_count")),
        forks_count=_int_value(data.get("forks_count")),
        open_issues_count=_int_value(data.get("open_issues_count")),
        subscribers_count=_int_value(data.get("subscribers_count")),
        owner_login=str(data.get("owner_login") or ""),
        owner_avatar_url=str(data.get("owner_avatar_url") or ""),
        license_name=str(data.get("license_name") or ""),
        github_created_at=cast("datetime", data["github_created_at"]),
        github_pushed_at=cast("datetime", data["github_pushed_at"]),
        rank=_int_value(data.get("rank")),
    )


def _to_language_breakdown(data: DashboardRow) -> LanguageBreakdownDTO:
    return LanguageBreakdownDTO(
        language=str(data.get("language") or "Unknown"),
        star_count=_int_value(data.get("star_count")),
        repo_count=_int_value(data.get("repo_count")),
    )


def _to_topic_breakdown(data: DashboardRow) -> TopicBreakdownDTO:
    return TopicBreakdownDTO(
        topic=str(data.get("topic") or ""),
        star_count=_int_value(data.get("star_count")),
        repo_count=_int_value(data.get("repo_count")),
    )


def _to_timeseries_point(data: DashboardRow) -> TimeseriesPointDTO:
    event_date = data.get("event_date")
    parsed_event_date = (
        event_date.date() if isinstance(event_date, datetime) else cast("date", event_date)
    )
    return TimeseriesPointDTO(
        event_date=parsed_event_date,
        star_count=_int_value(data.get("star_count")),
        total_events=_int_value(data.get("total_events")),
    )


def _to_category_summary(data: DashboardRow) -> CategorySummaryDTO:
    return CategorySummaryDTO(
        category=str(data.get("category") or "Other"),
        repo_count=_int_value(data.get("repo_count")),
        total_stars=_int_value(data.get("total_stars")),
        top_repo_name=str(data.get("top_repo_name") or ""),
        top_repo_stars=_int_value(data.get("top_repo_stars")),
        weekly_star_delta=_int_value(data.get("weekly_star_delta")),
    )


def _to_topic_rotation(data: DashboardRow) -> TopicRotationDTO:
    return TopicRotationDTO(
        topic=str(data.get("topic") or ""),
        current_star_count=_int_value(data.get("current_star_count")),
        previous_star_count=_int_value(data.get("previous_star_count")),
        star_delta=_int_value(data.get("star_delta")),
        repo_count=_int_value(data.get("repo_count")),
        rank=_int_value(data.get("rank")),
    )


def _int_value(value: object | None) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return 0
    return 0


def _float_value(value: object | None) -> float:
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return 0.0
    return 0.0


def _string_list(value: object | None) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, tuple):
        return [str(item) for item in value]
    return []
