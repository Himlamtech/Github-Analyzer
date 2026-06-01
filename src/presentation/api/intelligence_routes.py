"""Intelligence API endpoints for higher-level product views."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, cast

from fastapi import APIRouter, Depends, HTTPException, Query
import structlog

from src.application.dtos.intelligence_dto import (
    BreakoutRepositoryDTO,
    ExternalNewsPreviewItemDTO,
    ExternalNewsSourceHealthDTO,
    ExternalNewsSourcePreviewDTO,
    ExternalNewsSyncResultDTO,
    FrameworkRadarSnapshotDTO,
    NewsImpactEventDTO,
    NewsImpactReadinessDTO,
    RotationCategoryDTO,
    WeeklyBriefSnapshotDTO,
)
from src.application.use_cases.build_breakout_view import BuildBreakoutViewUseCase
from src.application.use_cases.build_rotation_view import BuildRotationViewUseCase
from src.application.use_cases.get_framework_radar_snapshot import (
    GetFrameworkRadarSnapshotUseCase,
)
from src.application.use_cases.get_news_impact_readiness import (
    GetNewsImpactReadinessUseCase,
)
from src.application.use_cases.get_news_impact_snapshot import GetNewsImpactSnapshotUseCase
from src.application.use_cases.get_weekly_brief_snapshot import GetWeeklyBriefSnapshotUseCase
from src.application.use_cases.list_persisted_external_news import (
    ListExternalNewsSourceHealthUseCase,
    ListPersistedExternalNewsItemsUseCase,
)
from src.application.use_cases.preview_external_news_sources import (
    PreviewExternalNewsSourcesUseCase,
)
from src.application.use_cases.sync_external_news_sources import SyncExternalNewsSourcesUseCase
from src.domain.exceptions import DashboardQueryError
from src.infrastructure.config import Settings, get_settings
from src.infrastructure.external_sources.rss_news_reader import RssNewsReader
from src.infrastructure.storage.clickhouse_external_news_repository import (
    ClickHouseExternalNewsRepository,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from src.domain.repositories.external_news_reader import ExternalNewsReaderABC
    from src.infrastructure.storage.clickhouse_dashboard_service import ClickHouseDashboardService

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/intelligence", tags=["Intelligence"])


async def _get_external_news_reader() -> AsyncIterator[object]:
    """Construct and close the official external news reader."""
    reader = RssNewsReader()
    try:
        yield reader
    finally:
        await reader.aclose()


def _get_external_news_repository(
    settings: Annotated[Settings, Depends(get_settings)],
) -> object:
    """Construct a ClickHouse-backed repository for external news persistence."""
    return ClickHouseExternalNewsRepository(
        host=settings.clickhouse_host,
        port=settings.clickhouse_port,
        user=settings.clickhouse_user,
        password=settings.clickhouse_password,
        database=settings.clickhouse_database,
    )


def _get_dashboard_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> object:
    """Construct a ClickHouseDashboardService for intelligence routes."""
    from src.infrastructure.storage.clickhouse_dashboard_service import (
        ClickHouseDashboardService,
    )

    return ClickHouseDashboardService(
        host=settings.clickhouse_host,
        port=settings.clickhouse_port,
        user=settings.clickhouse_user,
        password=settings.clickhouse_password,
        database=settings.clickhouse_database,
    )


@router.get("/breakout", response_model=list[BreakoutRepositoryDTO])
async def get_breakout(
    svc: Annotated[object, Depends(_get_dashboard_service)],
    category: Annotated[
        str | None,
        Query(description="Optional repository category filter."),
    ] = None,
    days: Annotated[int, Query(ge=1, le=90)] = 7,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[BreakoutRepositoryDTO]:
    """Return breakout intelligence derived from live dashboard analytics inputs."""
    service = cast("ClickHouseDashboardService", svc)
    use_case = BuildBreakoutViewUseCase(reader=service)

    try:
        return await use_case.execute(days=days, limit=limit, category=category)
    except DashboardQueryError as exc:
        logger.error("intelligence.breakout_failed", category=category, days=days, error=str(exc))
        raise HTTPException(status_code=503, detail="Breakout intelligence query failed") from exc


@router.get("/rotation", response_model=list[RotationCategoryDTO])
async def get_rotation(
    svc: Annotated[object, Depends(_get_dashboard_service)],
    days: Annotated[int, Query(ge=1, le=90)] = 7,
    limit: Annotated[int, Query(ge=1, le=20)] = 8,
) -> list[RotationCategoryDTO]:
    """Return ecosystem rotation intelligence derived from live dashboard analytics inputs."""
    service = cast("ClickHouseDashboardService", svc)
    use_case = BuildRotationViewUseCase(reader=service)

    try:
        return await use_case.execute(days=days, limit=limit)
    except DashboardQueryError as exc:
        logger.error("intelligence.rotation_failed", days=days, error=str(exc))
        raise HTTPException(status_code=503, detail="Rotation intelligence query failed") from exc


@router.get("/framework-radar", response_model=FrameworkRadarSnapshotDTO)
async def get_framework_radar() -> FrameworkRadarSnapshotDTO:
    """Return the current curated framework radar snapshot."""
    return GetFrameworkRadarSnapshotUseCase().execute()


@router.get("/news-impact", response_model=list[NewsImpactEventDTO])
async def get_news_impact() -> list[NewsImpactEventDTO]:
    """Return the current curated news-to-code impact snapshot."""
    return GetNewsImpactSnapshotUseCase().execute()


@router.get("/news-impact/readiness", response_model=NewsImpactReadinessDTO)
async def get_news_impact_readiness(
    settings: Annotated[Settings, Depends(get_settings)],
) -> NewsImpactReadinessDTO:
    """Return whether NewsImpact can be upgraded from curated snapshot to live ingestion."""
    return GetNewsImpactReadinessUseCase(settings=settings).execute()


@router.get(
    "/news-impact/sources/preview",
    response_model=list[ExternalNewsSourcePreviewDTO],
)
async def get_news_impact_source_preview(
    settings: Annotated[Settings, Depends(get_settings)],
    reader: Annotated[object, Depends(_get_external_news_reader)],
    limit_per_source: Annotated[int, Query(ge=1, le=10)] = 3,
) -> list[ExternalNewsSourcePreviewDTO]:
    """Fetch the latest items from enabled official external sources."""
    use_case = PreviewExternalNewsSourcesUseCase(
        reader=cast("ExternalNewsReaderABC", reader),
        settings=settings,
    )
    return await use_case.execute(limit_per_source=limit_per_source)


@router.post(
    "/news-impact/sources/sync",
    response_model=ExternalNewsSyncResultDTO,
)
async def sync_news_impact_sources(
    settings: Annotated[Settings, Depends(get_settings)],
    reader: Annotated[object, Depends(_get_external_news_reader)],
    repository: Annotated[object, Depends(_get_external_news_repository)],
    limit_per_source: Annotated[int, Query(ge=1, le=50)] = 10,
) -> ExternalNewsSyncResultDTO:
    """Fetch enabled official external feeds and persist latest items into ClickHouse."""
    use_case = SyncExternalNewsSourcesUseCase(
        reader=cast("ExternalNewsReaderABC", reader),
        repository=cast("ClickHouseExternalNewsRepository", repository),
        settings=settings,
    )
    return await use_case.execute(limit_per_source=limit_per_source)


@router.get(
    "/news-impact/sources/latest",
    response_model=list[ExternalNewsPreviewItemDTO],
)
async def get_persisted_news_impact_items(
    repository: Annotated[object, Depends(_get_external_news_repository)],
    provider: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[ExternalNewsPreviewItemDTO]:
    """Return latest persisted external news items from ClickHouse."""
    use_case = ListPersistedExternalNewsItemsUseCase(
        repository=cast("ClickHouseExternalNewsRepository", repository),
    )
    return await use_case.execute(provider=provider, limit=limit)


@router.get(
    "/news-impact/sources/health",
    response_model=list[ExternalNewsSourceHealthDTO],
)
async def get_news_impact_source_health(
    repository: Annotated[object, Depends(_get_external_news_repository)],
) -> list[ExternalNewsSourceHealthDTO]:
    """Return latest persisted health snapshot per official external source."""
    use_case = ListExternalNewsSourceHealthUseCase(
        repository=cast("ClickHouseExternalNewsRepository", repository),
    )
    return await use_case.execute()


@router.get("/weekly-brief/latest", response_model=WeeklyBriefSnapshotDTO)
async def get_weekly_brief_latest() -> WeeklyBriefSnapshotDTO:
    """Return the current curated weekly brief snapshot."""
    return GetWeeklyBriefSnapshotUseCase().execute()
