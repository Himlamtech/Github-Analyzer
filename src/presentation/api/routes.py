"""FastAPI route definitions — health check, pipeline status, and event queries.

Presentation layer: depends only on Application layer DTOs and
Infrastructure-level services via dependency injection.

Endpoints:
    GET /health                 — liveness probe
    GET /pipeline/status        — Kafka + ClickHouse connectivity check
    GET /events/latest          — most recent events from ClickHouse
    GET /events/top-repos       — top repos by star activity (DuckDB)
    GET /events/volume          — event type distribution for a date (DuckDB)
"""

from __future__ import annotations

from datetime import UTC
import json
import time
from typing import TYPE_CHECKING, Annotated, cast
from urllib.parse import quote
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
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
from src.infrastructure.observability.tracing import (
    get_current_trace_id,
    get_tracer,
    setup_tracing,
    shutdown_tracing,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from datetime import date

    from src.infrastructure.storage.clickhouse_repository import ClickHouseEventRepository
    from src.infrastructure.storage.duckdb_query_service import DuckDBQueryService

logger = structlog.get_logger(__name__)
tracer = get_tracer(__name__)
_PIPELINE_STALE_THRESHOLD_SECONDS = 300.0

app = FastAPI(
    title="GitHub AI Trend Analyzer API",
    version="0.2.0",
    description="Real-time ingestion status, dashboard analytics, and AI repository search.",
)

# Allow the Next.js dashboard frontend to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://frontend:3000",
    ],
    allow_methods=["GET"],
    allow_headers=["*"],
    expose_headers=["X-Request-Id", "X-Trace-Id", "X-Trace-Explore-Url"],
)

# Dashboard router (prefix: /dashboard)
from src.presentation.api.dashboard_routes import router as _dashboard_router  # noqa: E402

app.include_router(_dashboard_router)

# AI router (prefix: /ai)
from src.presentation.api.ai_routes import router as _ai_router  # noqa: E402

app.include_router(_ai_router)


# ── Dependency factories ──────────────────────────────────────────────────────


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


def _build_trace_explore_url(settings: Settings, trace_id: str) -> str:
    """Build a Grafana Explore deep link for a specific Tempo trace ID."""
    pane_state = {
        "trace": {
            "datasource": settings.tracing_grafana_tempo_datasource_uid,
            "queries": [
                {
                    "datasource": {
                        "type": "tempo",
                        "uid": settings.tracing_grafana_tempo_datasource_uid,
                    },
                    "limit": 20,
                    "query": trace_id,
                    "queryType": "traceqlSearch",
                    "refId": "A",
                }
            ],
            "range": {
                "from": settings.tracing_grafana_explore_from,
                "to": settings.tracing_grafana_explore_to,
            },
        }
    }
    encoded_panes = quote(json.dumps(pane_state, separators=(",", ":")), safe="")
    grafana_base_url = str(settings.tracing_grafana_base_url).rstrip("/")
    return (
        f"{grafana_base_url}/explore?orgId={settings.tracing_grafana_org_id}"
        f"&schemaVersion=1&panes={encoded_panes}"
    )


# ── Response models ───────────────────────────────────────────────────────────


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


# ── Startup hook ──────────────────────────────────────────────────────────────


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
        # Port already bound (e.g., duplicate container startup) — non-fatal
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
    setup_tracing(app, settings)


@app.on_event("shutdown")
async def _shutdown() -> None:
    """Flush tracing on shutdown."""
    shutdown_tracing()


@app.middleware("http")
async def _instrument_request(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Record HTTP metrics and expose the active trace ID in responses."""
    next_handler = call_next
    settings = get_settings()
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

    with tracer.start_as_current_span(f"{request.method} {request.url.path}") as span:
        try:
            response = await next_handler(request)
        finally:
            API_IN_FLIGHT_REQUESTS.dec()

        elapsed = time.perf_counter() - start_time
        status_code = str(response.status_code)

        span.set_attribute("http.method", request.method)
        span.set_attribute("http.route", route_path)
        span.set_attribute("http.status_code", response.status_code)
        span.set_attribute("gha.request.duration_seconds", elapsed)

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

        trace_id = get_current_trace_id()
        if trace_id is not None:
            bind_contextvars(trace_id=trace_id)
            response.headers["X-Trace-Id"] = trace_id
            response.headers["X-Trace-Explore-Url"] = _build_trace_explore_url(
                settings,
                trace_id,
            )

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


# ── Routes ────────────────────────────────────────────────────────────────────


@app.get("/health", response_model=HealthResponse, tags=["Infrastructure"])
async def health() -> HealthResponse:
    """Liveness probe — always returns 200 if the API is running."""
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
    """Check connectivity to ClickHouse and verify the Parquet archive path.

    Returns data freshness metric (seconds since last event written).
    """
    from pathlib import Path

    repo = cast("ClickHouseEventRepository", ch_repo)
    root_span = trace.get_current_span()
    ch_ok = False
    freshness: float | None = None
    parquet_exists = False

    with tracer.start_as_current_span("pipeline_status.check_parquet_path") as parquet_span:
        parquet_exists = Path(settings.parquet_base_path).exists()
        parquet_span.set_attribute("pipeline.parquet_path", settings.parquet_base_path)
        parquet_span.set_attribute("pipeline.parquet_path_exists", parquet_exists)
        if not parquet_exists:
            parquet_span.set_status(
                Status(
                    status_code=StatusCode.ERROR,
                    description="Parquet archive path is missing",
                )
            )

    with tracer.start_as_current_span(
        "pipeline_status.check_clickhouse_freshness"
    ) as clickhouse_span:
        try:
            max_ts = await repo.get_max_created_at()
            ch_ok = True
            clickhouse_span.set_attribute("pipeline.clickhouse_reachable", True)
            if max_ts is not None:
                freshness = time.time() - max_ts
                DATA_FRESHNESS_SECONDS.set(freshness)
                clickhouse_span.set_attribute("pipeline.data_freshness_seconds", freshness)
            else:
                clickhouse_span.set_attribute("pipeline.data_freshness_seconds", -1.0)
                clickhouse_span.set_status(
                    Status(
                        status_code=StatusCode.ERROR,
                        description="No events found in ClickHouse",
                    )
                )
        except Exception as exc:
            logger.warning("api.clickhouse_health_check_failed", error=str(exc))
            clickhouse_span.set_attribute("pipeline.clickhouse_reachable", False)
            clickhouse_span.set_attribute("pipeline.error", str(exc))
            clickhouse_span.set_status(
                Status(
                    status_code=StatusCode.ERROR,
                    description="ClickHouse health check failed",
                )
            )

    with tracer.start_as_current_span("pipeline_status.evaluate_status") as evaluation_span:
        stale = freshness is not None and freshness > _PIPELINE_STALE_THRESHOLD_SECONDS
        overall = "healthy" if (ch_ok and parquet_exists and not stale) else "degraded"
        evaluation_span.set_attribute("pipeline.status", overall)
        evaluation_span.set_attribute("pipeline.clickhouse_reachable", ch_ok)
        evaluation_span.set_attribute("pipeline.parquet_path_exists", parquet_exists)
        evaluation_span.set_attribute("pipeline.is_stale", stale)
        if freshness is not None:
            evaluation_span.set_attribute("pipeline.data_freshness_seconds", freshness)
        if stale:
            evaluation_span.set_attribute(
                "pipeline.root_cause_hint",
                "processing_pipeline_stalled",
            )
            evaluation_span.set_status(
                Status(
                    status_code=StatusCode.ERROR,
                    description="Pipeline is stale; processing appears stalled",
                )
            )
        elif overall != "healthy":
            evaluation_span.set_attribute(
                "pipeline.root_cause_hint",
                "storage_or_archive_unavailable",
            )
            evaluation_span.set_status(
                Status(
                    status_code=StatusCode.ERROR,
                    description="Pipeline dependencies are degraded",
                )
            )

    root_span.set_attribute("pipeline.status", overall)
    root_span.set_attribute("pipeline.clickhouse_reachable", ch_ok)
    root_span.set_attribute("pipeline.parquet_path_exists", parquet_exists)
    if freshness is not None:
        root_span.set_attribute("pipeline.data_freshness_seconds", freshness)
    if overall != "healthy":
        root_span.set_status(
            Status(
                status_code=StatusCode.ERROR,
                description="Pipeline status degraded",
            )
        )

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
    """Return the most recent events from ClickHouse.

    Args:
        limit:      Maximum number of events to return (1-500).
        event_type: Optional filter by event type (e.g., "WatchEvent").
    """
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
    """Return the top AI repositories by star count over the last N days.

    Queries the Parquet archive via DuckDB — no ClickHouse dependency.

    Args:
        days:  Look-back window in days.
        limit: Maximum number of repos.
    """
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
    """Return event type distribution for a given UTC date.

    Args:
        query_date: Date to aggregate (defaults to today UTC).
    """
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
    """Return per-hour event counts for a specific repository.

    Args:
        repo_name:  Repository in ``owner/repo`` format.
        query_date: UTC date (defaults to today).
    """
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
