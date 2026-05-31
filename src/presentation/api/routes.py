"""FastAPI route definitions for health, pipeline status, and event queries."""

from __future__ import annotations

from datetime import UTC
import time
from typing import TYPE_CHECKING, Annotated, cast
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import structlog
from structlog.contextvars import bind_contextvars, clear_contextvars

from src.application.dtos.github_event_dto import HourlyActivityDTO, RepoStarCountDTO
from src.infrastructure.config import Settings, get_settings
from src.infrastructure.observability.metrics import (
    API_IN_FLIGHT_REQUESTS,
    API_REQUEST_DURATION_SECONDS,
    API_REQUESTS_TOTAL,
    DATA_FRESHNESS_SECONDS,
    start_metrics_server,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from datetime import date

    from src.infrastructure.storage.clickhouse_repository import ClickHouseEventRepository
    from src.infrastructure.storage.duckdb_query_service import DuckDBQueryService

logger = structlog.get_logger(__name__)
_PIPELINE_STALE_THRESHOLD_SECONDS = 300.0

app = FastAPI(
    title="GitHub Analyzer API",
    version="0.2.0",
    description="Real-time ingestion status and dashboard analytics for GitHub events.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://frontend:3000",
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
    expose_headers=["X-Request-Id"],
)

from src.presentation.api.dashboard_routes import router as _dashboard_router  # noqa: E402

app.include_router(_dashboard_router)


def _get_clickhouse_repo(
    settings: Annotated[Settings, Depends(get_settings)],
) -> object:
    """Construct a ClickHouseEventRepository for the request."""
    from src.infrastructure.storage.clickhouse_repository import ClickHouseEventRepository

    return ClickHouseEventRepository(
        host=settings.clickhouse_host,
        port=settings.clickhouse_port,
        user=settings.clickhouse_user,
        password=settings.clickhouse_password,
        database=settings.clickhouse_database,
    )


def _get_duckdb_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> object:
    """Construct a DuckDBQueryService for the request."""
    from src.infrastructure.storage.duckdb_query_service import DuckDBQueryService

    return DuckDBQueryService(base_path=settings.parquet_base_path)


class HealthResponse(BaseModel):
    """Liveness probe response."""

    status: str
    timestamp: float


class PipelineStatusResponse(BaseModel):
    """Operational status of all pipeline components."""

    clickhouse_reachable: bool
    parquet_path_exists: bool
    data_freshness_seconds: float | None
    status: str


class EventSummaryResponse(BaseModel):
    """Summary of a single GitHub event returned by the API."""

    event_id: str
    event_type: str
    actor_login: str
    repo_name: str
    created_at: str


@app.on_event("startup")
async def _startup() -> None:
    """Start Prometheus metrics HTTP server on startup."""
    from src.infrastructure.storage.clickhouse_repo_observation_bootstrap import (
        ClickHouseRepoObservationBootstrapService,
    )

    settings = get_settings()
    try:
        start_metrics_server(port=settings.metrics_port)
        logger.info("api.metrics_server_started", port=settings.metrics_port)
    except OSError as exc:
        logger.warning("api.metrics_server_port_busy", error=str(exc))
    try:
        await ClickHouseRepoObservationBootstrapService(
            host=settings.clickhouse_host,
            port=settings.clickhouse_port,
            user=settings.clickhouse_user,
            password=settings.clickhouse_password,
            database=settings.clickhouse_database,
        ).execute()
    except Exception as exc:
        logger.error("api.clickhouse_repo_observation_bootstrap_failed", error=str(exc))


@app.middleware("http")
async def _instrument_request(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Record HTTP metrics and expose the request ID in responses."""
    start_time = time.perf_counter()
    API_IN_FLIGHT_REQUESTS.inc()
    request_id = request.headers.get("X-Request-ID", str(uuid4()))
    route_template = request.scope.get("route")
    route_path = getattr(route_template, "path", request.url.path)
    clear_contextvars()
    bind_contextvars(
        request_id=request_id,
        http_method=request.method,
        http_route=route_path,
        http_path=request.url.path,
    )

    try:
        response = await call_next(request)
    finally:
        API_IN_FLIGHT_REQUESTS.dec()

    elapsed = time.perf_counter() - start_time
    status_code = str(response.status_code)

    API_REQUESTS_TOTAL.labels(
        method=request.method,
        route=route_path,
        status_code=status_code,
    ).inc()
    API_REQUEST_DURATION_SECONDS.labels(
        method=request.method,
        route=route_path,
        status_code=status_code,
    ).observe(elapsed)

    response.headers["X-Request-Id"] = request_id
    bind_contextvars(
        http_status_code=response.status_code,
        request_duration_ms=round(elapsed * 1000, 2),
    )
    logger.info(
        "api.request.completed",
        request_id=request_id,
        method=request.method,
        route=route_path,
        status_code=response.status_code,
        duration_ms=round(elapsed * 1000, 2),
    )
    return response


@app.get("/health", response_model=HealthResponse, tags=["Infrastructure"])
async def health() -> HealthResponse:
    """Liveness probe that returns 200 while the API process is up."""
    return HealthResponse(status="ok", timestamp=time.time())


@app.get(
    "/pipeline/status",
    response_model=PipelineStatusResponse,
    tags=["Infrastructure"],
)
async def pipeline_status(
    settings: Annotated[Settings, Depends(get_settings)],
    ch_repo: Annotated[object, Depends(_get_clickhouse_repo)],
) -> PipelineStatusResponse:
    """Check ClickHouse connectivity and Parquet archive availability."""
    from pathlib import Path

    repo = cast("ClickHouseEventRepository", ch_repo)
    ch_ok = False
    freshness: float | None = None
    parquet_exists = Path(settings.parquet_base_path).exists()

    try:
        max_ts = await repo.get_max_created_at()
        ch_ok = True
        if max_ts is not None:
            freshness = time.time() - max_ts
            DATA_FRESHNESS_SECONDS.set(freshness)
    except Exception as exc:
        logger.warning("api.clickhouse_health_check_failed", error=str(exc))

    stale = freshness is not None and freshness > _PIPELINE_STALE_THRESHOLD_SECONDS
    overall = "healthy" if (ch_ok and parquet_exists and not stale) else "degraded"

    return PipelineStatusResponse(
        clickhouse_reachable=ch_ok,
        parquet_path_exists=parquet_exists,
        data_freshness_seconds=freshness,
        status=overall,
    )


@app.get(
    "/events/latest",
    response_model=list[EventSummaryResponse],
    tags=["Events"],
)
async def get_latest_events(
    ch_repo: Annotated[object, Depends(_get_clickhouse_repo)],
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
    event_type: Annotated[str | None, Query()] = None,
) -> list[EventSummaryResponse]:
    """Return the most recent events from ClickHouse."""
    from datetime import datetime

    repo = cast("ClickHouseEventRepository", ch_repo)
    today = datetime.now(tz=UTC).date()
    try:
        events = await repo.find_by_date_range(
            start=today,
            end=today,
            limit=limit,
        )
    except Exception as exc:
        logger.error("api.get_latest_events_failed", error=str(exc))
        raise HTTPException(status_code=503, detail="ClickHouse unavailable") from exc

    filtered = [e for e in events if event_type is None or str(e.event_type) == event_type]

    return [
        EventSummaryResponse(
            event_id=e.event_id,
            event_type=str(e.event_type),
            actor_login=e.actor_login,
            repo_name=str(e.repo_id),
            created_at=e.created_at.isoformat(),
        )
        for e in filtered[:limit]
    ]


@app.get(
    "/events/top-repos",
    response_model=list[RepoStarCountDTO],
    tags=["Analytics"],
)
async def get_top_repos(
    duckdb_svc: Annotated[object, Depends(_get_duckdb_service)],
    days: Annotated[int, Query(ge=1, le=90)] = 7,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[RepoStarCountDTO]:
    """Return the top repositories by star count over the last N days."""
    svc = cast("DuckDBQueryService", duckdb_svc)
    try:
        return await svc.get_top_repos_by_stars(days=days, limit=limit)
    except Exception as exc:
        logger.error("api.get_top_repos_failed", error=str(exc))
        raise HTTPException(status_code=503, detail="Query failed") from exc


@app.get(
    "/events/volume",
    response_model=dict[str, int],
    tags=["Analytics"],
)
async def get_event_volume(
    duckdb_svc: Annotated[object, Depends(_get_duckdb_service)],
    query_date: Annotated[date | None, Query()] = None,
) -> dict[str, int]:
    """Return event type distribution for a given UTC date."""
    from datetime import datetime

    svc = cast("DuckDBQueryService", duckdb_svc)
    target_date = query_date or datetime.now(tz=UTC).date()

    try:
        return await svc.get_event_volume_by_type(target_date)
    except Exception as exc:
        logger.error("api.get_event_volume_failed", error=str(exc))
        raise HTTPException(status_code=503, detail="Query failed") from exc


@app.get(
    "/events/hourly",
    response_model=list[HourlyActivityDTO],
    tags=["Analytics"],
)
async def get_hourly_activity(
    duckdb_svc: Annotated[object, Depends(_get_duckdb_service)],
    repo_name: Annotated[str, Query(min_length=3)],
    query_date: Annotated[date | None, Query()] = None,
) -> list[HourlyActivityDTO]:
    """Return per-hour event counts for a specific repository."""
    from datetime import datetime

    svc = cast("DuckDBQueryService", duckdb_svc)
    target_date = query_date or datetime.now(tz=UTC).date()

    try:
        return await svc.get_hourly_activity(repo_name=repo_name, query_date=target_date)
    except Exception as exc:
        logger.error(
            "api.get_hourly_activity_failed",
            repo=repo_name,
            error=str(exc),
        )
        raise HTTPException(status_code=503, detail="Query failed") from exc
