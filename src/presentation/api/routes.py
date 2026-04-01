"""FastAPI composition root for API endpoints."""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

from clickhouse_driver import Client
from clickhouse_driver.errors import Error as ClickHouseDriverError
from clickhouse_driver.errors import NetworkError as ClickHouseDriverNetworkError
from fastapi import Depends, FastAPI, Request, Response
from opentelemetry import trace

from src.domain.exceptions import ClickHouseConnectionError
from src.infrastructure.config import Settings, get_settings
from src.infrastructure.observability.tracing import (
    PipelineRootCause,
    PipelineStatus,
    annotate_pipeline_span,
    get_current_trace_id,
    get_tracer,
    setup_tracing,
    shutdown_tracing,
)
from src.presentation.api import ai_routes, dashboard_routes

if TYPE_CHECKING:
    from src.infrastructure.storage.clickhouse_repo_observation_bootstrap import (
        ClickHouseRepoObservationBootstrapService,
    )


PIPELINE_STALE_THRESHOLD_SECONDS = 600.0
tracer = get_tracer(__name__)


class ClickHouseHealthRepository:
    """Minimal repository for health-oriented ClickHouse checks."""

    def __init__(
        self,
        *,
        host: str,
        port: int,
        user: str,
        password: str,
        database: str,
    ) -> None:
        self._host = host
        self._port = port
        self._user = user
        self._password = password
        self._database = database

    def _get_client(self) -> Client:
        try:
            return Client(
                host=self._host,
                port=self._port,
                user=self._user,
                password=self._password,
                database=self._database,
                connect_timeout=10,
                send_receive_timeout=30,
                sync_request_timeout=5,
                settings={"use_client_time_zone": True},
            )
        except ClickHouseDriverNetworkError as exc:
            raise ClickHouseConnectionError(
                f"Cannot connect to ClickHouse at {self._host}:{self._port}: {exc}"
            ) from exc

    async def get_max_created_at(self) -> float | None:
        """Return the latest event timestamp as a UTC epoch seconds value."""

        def _run() -> float | None:
            client = self._get_client()
            try:
                rows = client.execute("SELECT max(created_at) FROM github_data")
            except ClickHouseDriverError as exc:
                raise ClickHouseConnectionError(f"ClickHouse health query failed: {exc}") from exc
            if not rows or rows[0][0] is None:
                return None
            value = rows[0][0]
            if isinstance(value, datetime):
                parsed = value if value.tzinfo else value.replace(tzinfo=UTC)
                return parsed.timestamp()
            return None

        return await asyncio.to_thread(_run)


def _get_clickhouse_repo(
    settings: Annotated[Settings, Depends(get_settings)],
) -> ClickHouseHealthRepository:
    """Construct the ClickHouse health repository for the request."""

    return ClickHouseHealthRepository(
        host=settings.clickhouse_host,
        port=settings.clickhouse_port,
        user=settings.clickhouse_user,
        password=settings.clickhouse_password,
        database=settings.clickhouse_database,
    )


def start_metrics_server(port: int = 9001) -> None:
    """Best-effort Prometheus exporter bootstrap."""

    try:
        from prometheus_client import start_http_server
    except ModuleNotFoundError:
        return

    try:
        start_http_server(port)
    except OSError:
        return


def _get_repo_observation_bootstrap_service(
    settings: Settings,
) -> ClickHouseRepoObservationBootstrapService:
    """Construct the repo-observation bootstrap service."""

    from src.infrastructure.storage.clickhouse_repo_observation_bootstrap import (
        ClickHouseRepoObservationBootstrapService,
    )

    return ClickHouseRepoObservationBootstrapService(
        host=settings.clickhouse_host,
        port=settings.clickhouse_port,
        user=settings.clickhouse_user,
        password=settings.clickhouse_password,
        database=settings.clickhouse_database,
    )


def _build_trace_explore_url(trace_id: str) -> str:
    return (
        "/explore?left="
        f"%7B%22datasource%22%3A%22tempo_ds%22%2C%22queries%22%3A"
        f"%5B%7B%22query%22%3A%22{trace_id}%22%7D%5D%7D"
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialize and tear down API-level runtime hooks."""
    settings = get_settings()
    start_metrics_server()
    setup_tracing(app, settings)
    bootstrap_service = _get_repo_observation_bootstrap_service(settings)
    try:
        await bootstrap_service.execute()
    except ClickHouseConnectionError:
        pass
    try:
        yield
    finally:
        shutdown_tracing()


app = FastAPI(title="GitHub AI Analyzer API", version="1.0.1", lifespan=lifespan)
app.include_router(ai_routes.router)
app.include_router(dashboard_routes.router)


@app.middleware("http")
async def attach_request_headers(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Attach request and trace metadata headers to every response."""

    request_id = request.headers.get("X-Request-Id") or uuid.uuid4().hex
    response = await call_next(request)
    trace_id = get_current_trace_id()

    response.headers["X-Request-Id"] = request_id
    if trace_id is not None:
        response.headers["X-Trace-Id"] = trace_id
        response.headers["X-Trace-Explore-Url"] = _build_trace_explore_url(trace_id)
    response.headers["Access-Control-Expose-Headers"] = (
        "X-Request-Id, X-Trace-Id, X-Trace-Explore-Url"
    )
    return response


@app.get("/health")
async def health() -> dict[str, str]:
    """Cheap liveness endpoint."""

    return {"status": "ok"}


@app.get("/pipeline/status")
async def pipeline_status(
    response: Response,
    settings: Annotated[Settings, Depends(get_settings)],
    clickhouse_repo: Annotated[ClickHouseHealthRepository, Depends(_get_clickhouse_repo)],
) -> dict[str, object]:
    """Return a business-facing pipeline freshness verdict."""

    trace_id = get_current_trace_id()
    if trace_id is not None:
        response.headers["X-Trace-Id"] = trace_id

    parquet_path = Path(settings.parquet_base_path)
    parquet_exists = parquet_path.exists()
    root_span = trace.get_current_span()

    with tracer.start_as_current_span("pipeline_status.evaluate_status") as child_span:
        try:
            max_created_at = await clickhouse_repo.get_max_created_at()
            freshness_seconds = None
            root_cause = PipelineRootCause.NONE
            status = PipelineStatus.HEALTHY

            if max_created_at is None:
                status = PipelineStatus.DEGRADED if parquet_exists else PipelineStatus.UNAVAILABLE
                root_cause = (
                    PipelineRootCause.NO_EVENTS_FOUND
                    if parquet_exists
                    else PipelineRootCause.PARQUET_ARCHIVE_MISSING
                )
            else:
                freshness_seconds = max(0.0, datetime.now(tz=UTC).timestamp() - max_created_at)
                if freshness_seconds > PIPELINE_STALE_THRESHOLD_SECONDS:
                    status = PipelineStatus.DEGRADED
                    root_cause = PipelineRootCause.PROCESSING_PIPELINE_STALLED

            annotate_pipeline_span(
                span=child_span,
                status=status,
                freshness_seconds=freshness_seconds,
                parquet_path=str(parquet_path),
                parquet_path_exists=parquet_exists,
                clickhouse_reachable=True,
                spark_suspected_failure=root_cause
                is PipelineRootCause.PROCESSING_PIPELINE_STALLED,
                business_stale=status is not PipelineStatus.HEALTHY,
                root_cause_hint=root_cause,
                trace_id=trace_id,
            )
            annotate_pipeline_span(
                span=root_span,
                status=status,
                freshness_seconds=freshness_seconds,
                parquet_path=str(parquet_path),
                parquet_path_exists=parquet_exists,
                clickhouse_reachable=True,
                spark_suspected_failure=root_cause
                is PipelineRootCause.PROCESSING_PIPELINE_STALLED,
                business_stale=status is not PipelineStatus.HEALTHY,
                root_cause_hint=root_cause,
                trace_id=trace_id,
            )

            return {
                "status": status.value,
                "data_freshness_seconds": freshness_seconds,
                "root_cause_hint": root_cause.value,
                "parquet_path": str(parquet_path),
                "parquet_path_exists": parquet_exists,
                "trace_id": trace_id,
            }
        except ClickHouseConnectionError:
            status = PipelineStatus.UNAVAILABLE
            root_cause = PipelineRootCause.CLICKHOUSE_UNREACHABLE
            annotate_pipeline_span(
                span=child_span,
                status=status,
                freshness_seconds=None,
                parquet_path=str(parquet_path),
                parquet_path_exists=parquet_exists,
                clickhouse_reachable=False,
                spark_suspected_failure=False,
                business_stale=True,
                root_cause_hint=root_cause,
                trace_id=trace_id,
            )
            annotate_pipeline_span(
                span=root_span,
                status=status,
                freshness_seconds=None,
                parquet_path=str(parquet_path),
                parquet_path_exists=parquet_exists,
                clickhouse_reachable=False,
                spark_suspected_failure=False,
                business_stale=True,
                root_cause_hint=root_cause,
                trace_id=trace_id,
            )
            return {
                "status": status.value,
                "data_freshness_seconds": None,
                "root_cause_hint": root_cause.value,
                "parquet_path": str(parquet_path),
                "parquet_path_exists": parquet_exists,
                "trace_id": trace_id,
            }
