"""OpenTelemetry tracing bootstrap for the FastAPI API service."""

from __future__ import annotations

from typing import TYPE_CHECKING

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.sampling import ParentBasedTraceIdRatio
import structlog

if TYPE_CHECKING:
    from fastapi import FastAPI

    from src.infrastructure.config import Settings

logger = structlog.get_logger(__name__)

_provider_initialized = False
_httpx_instrumented = False


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
