"""OpenTelemetry tracing bootstrap for the FastAPI API service."""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING

import structlog
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.sampling import ParentBasedTraceIdRatio
from opentelemetry.trace import Status, StatusCode

if TYPE_CHECKING:
    from fastapi import FastAPI

    from src.infrastructure.config import Settings

logger = structlog.get_logger(__name__)

_provider_initialized = False
_httpx_instrumented = False


class PipelineRootCause(StrEnum):
    """Root-cause hints attached to traces for pipeline investigations."""

    NONE = "none"
    PROCESSING_PIPELINE_STALLED = "processing_pipeline_stalled"
    CLICKHOUSE_UNREACHABLE = "clickhouse_unreachable"
    PARQUET_ARCHIVE_MISSING = "parquet_archive_missing"
    NO_EVENTS_FOUND = "no_events_found"


class PipelineStatus(StrEnum):
    """Normalized pipeline statuses exposed to trace viewers."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


def setup_tracing(app: FastAPI, settings: Settings) -> None:
    """Configure OpenTelemetry for the API process.

    Args:
        app: FastAPI application instance to instrument.
        settings: Runtime settings with tracing configuration.
    """
    global _provider_initialized, _httpx_instrumented

    if not settings.tracing_enabled:
        logger.info("tracing.disabled")
        return

    if not _provider_initialized:
        resource = Resource.create(
            {
                "service.name": settings.tracing_service_name,
                "deployment.environment": "local",
                "project.name": "gha",
            }
        )
        provider = TracerProvider(
            resource=resource,
            sampler=ParentBasedTraceIdRatio(settings.tracing_sampling_ratio),
        )
        exporter = OTLPSpanExporter(endpoint=str(settings.tracing_exporter_otlp_endpoint))
        provider.add_span_processor(SimpleSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        _provider_initialized = True
        logger.info(
            "tracing.provider_initialized",
            service_name=settings.tracing_service_name,
            exporter_endpoint=str(settings.tracing_exporter_otlp_endpoint),
            sampling_ratio=settings.tracing_sampling_ratio,
        )

    if not _httpx_instrumented:
        HTTPXClientInstrumentor().instrument()
        _httpx_instrumented = True
        logger.info("tracing.httpx_instrumented")

    if not getattr(app.state, "tracing_instrumented", False):
        FastAPIInstrumentor.instrument_app(app)
        app.state.tracing_instrumented = True
        logger.info("tracing.fastapi_instrumented")


def shutdown_tracing() -> None:
    """Flush and shutdown the active OpenTelemetry tracer provider."""
    provider = trace.get_tracer_provider()
    shutdown = getattr(provider, "shutdown", None)
    if callable(shutdown):
        cast_shutdown = shutdown
        cast_shutdown()
        logger.info("tracing.provider_shutdown")


def get_tracer(name: str) -> trace.Tracer:
    """Return a tracer scoped to the given module name."""
    return trace.get_tracer(name)


def get_current_trace_id() -> str | None:
    """Return the current trace ID as a 32-char hex string when available."""
    span = trace.get_current_span()
    context = span.get_span_context()
    if not context.is_valid:
        return None
    return format(context.trace_id, "032x")


def annotate_pipeline_span(
    *,
    span: trace.Span,
    status: PipelineStatus,
    freshness_seconds: float | None,
    parquet_path: str | None = None,
    parquet_path_exists: bool | None = None,
    clickhouse_reachable: bool | None = None,
    spark_suspected_failure: bool | None = None,
    business_stale: bool | None = None,
    root_cause_hint: PipelineRootCause = PipelineRootCause.NONE,
    trace_id: str | None = None,
) -> None:
    """Attach business-facing pipeline verdict attributes to a span.

    Args:
        span: Span to enrich.
        status: Current pipeline health verdict.
        freshness_seconds: Seconds since the latest successful record write.
        parquet_path: Archive path checked by the request.
        parquet_path_exists: Whether the archive path exists.
        clickhouse_reachable: Whether ClickHouse responded successfully.
        spark_suspected_failure: Whether the request strongly suggests Spark is stalled.
        business_stale: Whether the business freshness SLA is breached.
        root_cause_hint: Root-cause hint shown in trace drilldowns.
        trace_id: Correlation identifier exposed to API callers.
    """
    span.set_attribute("pipeline.status", status.value)
    span.set_attribute("pipeline.root_cause_hint", root_cause_hint.value)

    if freshness_seconds is not None:
        span.set_attribute("pipeline.data_freshness_seconds", freshness_seconds)
    if parquet_path is not None:
        span.set_attribute("pipeline.parquet_path", parquet_path)
    if parquet_path_exists is not None:
        span.set_attribute("pipeline.parquet_path_exists", parquet_path_exists)
    if clickhouse_reachable is not None:
        span.set_attribute("pipeline.clickhouse_reachable", clickhouse_reachable)
    if spark_suspected_failure is not None:
        span.set_attribute("spark.suspected_failure", spark_suspected_failure)
    if business_stale is not None:
        span.set_attribute("business.stale", business_stale)
    if trace_id is not None:
        span.set_attribute("correlation.trace_id", trace_id)

    if status is not PipelineStatus.HEALTHY:
        span.set_status(
            Status(
                status_code=StatusCode.ERROR,
                description=f"pipeline_status={status.value}; root_cause={root_cause_hint.value}",
            )
        )
