"""Intelligence API endpoints for higher-level product views."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, cast

from fastapi import APIRouter, Depends, HTTPException, Query
import structlog

from src.application.dtos.intelligence_dto import (
    BreakoutRepositoryDTO,
    FrameworkRadarSnapshotDTO,
    RotationCategoryDTO,
    WeeklyBriefSnapshotDTO,
)
from src.application.use_cases.build_breakout_view import BuildBreakoutViewUseCase
from src.application.use_cases.build_rotation_view import BuildRotationViewUseCase
from src.application.use_cases.get_framework_radar_snapshot import (
    GetFrameworkRadarSnapshotUseCase,
)
from src.application.use_cases.get_weekly_brief_snapshot import GetWeeklyBriefSnapshotUseCase
from src.domain.exceptions import DashboardQueryError
from src.infrastructure.config import Settings, get_settings

if TYPE_CHECKING:
    from src.infrastructure.storage.clickhouse_dashboard_service import ClickHouseDashboardService

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/intelligence", tags=["Intelligence"])


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


@router.get("/weekly-brief/latest", response_model=WeeklyBriefSnapshotDTO)
async def get_weekly_brief_latest() -> WeeklyBriefSnapshotDTO:
    """Return the current curated weekly brief snapshot."""
    return GetWeeklyBriefSnapshotUseCase().execute()
