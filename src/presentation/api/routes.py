"""FastAPI route definitions for health, pipeline status, and recent events."""

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

from src.infrastructure.config import Settings, get_settings

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from src.infrastructure.storage.clickhouse_repository import ClickHouseEventRepository

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


@app.middleware("http")
async def _instrument_request(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Bind request context and expose the request ID in responses."""
    start_time = time.perf_counter()
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

    response = await call_next(request)

    elapsed = time.perf_counter() - start_time

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
