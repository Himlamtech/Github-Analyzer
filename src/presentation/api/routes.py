"""FastAPI application entrypoint with observability instrumentation."""

from __future__ import annotations

from datetime import UTC
from pathlib import Path
from time import perf_counter, time
from typing import TYPE_CHECKING, Annotated
from urllib.parse import quote
from uuid import uuid4
import json

from fastapi import Depends, FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from opentelemetry import trace
from pydantic import BaseModel
import structlog
from structlog.contextvars import bind_contextvars, clear_contextvars

from src.infrastructure.config import Settings, get_settings
from src.infrastructure.observability.metrics import (
    API_IN_FLIGHT_REQUESTS,
    API_REQUEST_DURATION_SECONDS,
    API_REQUESTS_TOTAL,
    DATA_FRESHNESS_SECONDS,
    set_pipeline_status,
    start_metrics_server,
)
from src.infrastructure.observability.tracing import (
    PipelineRootCause,
    PipelineStatus,
    annotate_pipeline_span,
    get_current_trace_id,
    get_tracer,
    setup_tracing,
    shutdown_tracing,
)
from src.presentation.api.ai_routes import router as ai_router

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

logger = structlog.get_logger(__name__)
tracer = get_tracer(__name__)

app = FastAPI(
    title="GitHub AI Analyzer API",
    version="1.0.1",
    description="GitHub trend analysis backend with AI search and observability.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://frontend:3000"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Request-Id", "X-Trace-Id", "X-Trace-Explore-Url"],
)

app.include_router(ai_router)


class HealthResponse(BaseModel):
    """Basic liveness response."""

    status: str
    timestamp: float


class MetricsHealthResponse(BaseModel):
    """Metrics server configuration response."""

    enabled: bool
    port: int


class PipelineStatusResponse(BaseModel):
    """Operational status of storage and freshness signals."""

    clickhouse_reachable: bool
    parquet_path_exists: bool
    data_freshness_seconds: float | None
    status: str
    root_cause_hint: str


def _get_clickhouse_repo(settings: Annotated[Settings, Depends(get_settings)]) -> object:
    """Construct the ClickHouse event repository used by diagnostics."""
    from src.infrastructure.storage.clickhouse_repository import ClickHouseEventRepository

    return ClickHouseEventRepository(
        host=settings.clickhouse_host,
        port=settings.clickhouse_port,
        user=settings.clickhouse_user,
        password=settings.clickhouse_password,
        database=settings.clickhouse_database,
    )


def _build_trace_explore_url(settings: Settings, trace_id: str) -> str:
    pane_state = {
        "trace": {
            "datasource": settings.tracing_grafana_tempo_datasource_uid,
            "queries": [
                {
                    "datasource": {
                        "type": "tempo",
                        "uid": settings.tracing_grafana_tempo_datasource_uid,
                    },
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


@app.on_event("startup")
async def _startup() -> None:
    settings = get_settings()
    if settings.metrics_enabled:
        try:
            start_metrics_server(settings.metrics_port)
        except OSError as exc:
            logger.warning("metrics.server_unavailable", port=settings.metrics_port, error=str(exc))
    setup_tracing(app, settings)


@app.on_event("shutdown")
async def _shutdown() -> None:
    shutdown_tracing()


@app.middleware("http")
async def _instrument_request(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    settings = get_settings()
    start_time = perf_counter()
    request_id = request.headers.get("X-Request-ID", str(uuid4()))
    route_template = request.scope.get("route")
    route_path = getattr(route_template, "path", request.url.path)

    clear_contextvars()
    bind_contextvars(request_id=request_id, http_method=request.method, http_path=request.url.path)
    API_IN_FLIGHT_REQUESTS.inc()

    with tracer.start_as_current_span(f"{request.method} {request.url.path}") as span:
        try:
            response = await call_next(request)
        finally:
            API_IN_FLIGHT_REQUESTS.dec()

        elapsed = perf_counter() - start_time
        status_code = str(response.status_code)
        route_template = request.scope.get("route")
        route_path = getattr(route_template, "path", request.url.path)

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
            response.headers["X-Trace-Explore-Url"] = _build_trace_explore_url(settings, trace_id)

        response.headers["X-Request-Id"] = request_id
        logger.info(
            "api.request.completed",
            method=request.method,
            route=route_path,
            status_code=response.status_code,
            duration_ms=round(elapsed * 1000, 2),
        )
        return response


@app.get("/health", response_model=HealthResponse, tags=["Infrastructure"])
async def health() -> HealthResponse:
    """Return API liveness."""
    return HealthResponse(status="ok", timestamp=time())


@app.get("/metrics-health", response_model=MetricsHealthResponse, tags=["Infrastructure"])
async def metrics_health(
    settings: Annotated[Settings, Depends(get_settings)],
) -> MetricsHealthResponse:
    """Return metrics server configuration for smoke checks."""
    return MetricsHealthResponse(enabled=settings.metrics_enabled, port=settings.metrics_port)


@app.get("/pipeline/status", response_model=PipelineStatusResponse, tags=["Infrastructure"])
async def pipeline_status(
    settings: Annotated[Settings, Depends(get_settings)],
    ch_repo: Annotated[object, Depends(_get_clickhouse_repo)],
) -> PipelineStatusResponse:
    """Return ClickHouse reachability, archive presence, and data freshness."""
    root_span = trace.get_current_span()
    parquet_path_exists = Path(settings.parquet_base_path).exists()
    clickhouse_reachable = False
    freshness_seconds: float | None = None
    root_cause = PipelineRootCause.NONE

    with tracer.start_as_current_span("pipeline_status.check_clickhouse_freshness") as span:
        try:
            max_created_at = await ch_repo.get_max_created_at()  # type: ignore[attr-defined]
            clickhouse_reachable = True
            span.set_attribute("pipeline.clickhouse_reachable", True)
            if max_created_at is None:
                root_cause = PipelineRootCause.NO_EVENTS_FOUND
            else:
                freshness_seconds = _freshness_seconds(max_created_at)
                DATA_FRESHNESS_SECONDS.set(freshness_seconds)
                span.set_attribute("pipeline.data_freshness_seconds", freshness_seconds)
        except Exception as exc:
            clickhouse_reachable = False
            root_cause = PipelineRootCause.CLICKHOUSE_UNREACHABLE
            span.set_attribute("pipeline.clickhouse_reachable", False)
            span.set_attribute("pipeline.error", str(exc))

    if not parquet_path_exists and root_cause is PipelineRootCause.NONE:
        root_cause = PipelineRootCause.PARQUET_ARCHIVE_MISSING
    if (
        freshness_seconds is not None
        and freshness_seconds > settings.pipeline_stale_threshold_seconds
    ):
        root_cause = PipelineRootCause.PROCESSING_PIPELINE_STALLED

    status = (
        PipelineStatus.HEALTHY
        if clickhouse_reachable
        and parquet_path_exists
        and root_cause is PipelineRootCause.NONE
        else PipelineStatus.DEGRADED
    )
    set_pipeline_status(status.value)

    annotate_pipeline_span(
        span=root_span,
        status=status,
        freshness_seconds=freshness_seconds,
        parquet_path=settings.parquet_base_path,
        parquet_path_exists=parquet_path_exists,
        clickhouse_reachable=clickhouse_reachable,
        business_stale=root_cause is PipelineRootCause.PROCESSING_PIPELINE_STALLED,
        root_cause_hint=root_cause,
        trace_id=get_current_trace_id(),
    )

    with tracer.start_as_current_span("pipeline_status.evaluate_status") as span:
        annotate_pipeline_span(
            span=span,
            status=status,
            freshness_seconds=freshness_seconds,
            parquet_path=settings.parquet_base_path,
            parquet_path_exists=parquet_path_exists,
            clickhouse_reachable=clickhouse_reachable,
            business_stale=root_cause is PipelineRootCause.PROCESSING_PIPELINE_STALLED,
            root_cause_hint=root_cause,
            trace_id=get_current_trace_id(),
        )

    return PipelineStatusResponse(
        clickhouse_reachable=clickhouse_reachable,
        parquet_path_exists=parquet_path_exists,
        data_freshness_seconds=freshness_seconds,
        status=status.value,
        root_cause_hint=root_cause.value,
    )


def _freshness_seconds(max_created_at: object) -> float:
    if isinstance(max_created_at, int | float):
        return max(time() - float(max_created_at), 0.0)
    timestamp = getattr(max_created_at, "timestamp", None)
    if callable(timestamp):
        value = max_created_at
        if getattr(value, "tzinfo", None) is None:
            value = value.replace(tzinfo=UTC)
        return max(time() - float(value.timestamp()), 0.0)
    return 0.0
