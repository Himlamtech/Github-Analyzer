"""Prometheus metrics used by the API and observability dashboards."""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram, start_http_server
import structlog

logger = structlog.get_logger(__name__)

API_REQUESTS_TOTAL = Counter(
    "api_requests_total",
    "Total API requests processed by the FastAPI service.",
    ("method", "route", "status_code"),
)

API_REQUEST_DURATION_SECONDS = Histogram(
    "api_request_duration_seconds",
    "API request duration in seconds.",
    ("method", "route", "status_code"),
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

API_IN_FLIGHT_REQUESTS = Gauge(
    "api_in_flight_requests",
    "Number of API requests currently being processed.",
)

DATA_FRESHNESS_SECONDS = Gauge(
    "data_freshness_seconds",
    "Seconds since the latest event timestamp observed in ClickHouse.",
)

PIPELINE_STATUS = Gauge(
    "pipeline_status",
    "Pipeline status flag by state. Healthy state is 1 when active, otherwise 0.",
    ("status",),
)

AI_REQUESTS_TOTAL = Counter(
    "ai_requests_total",
    "Total AI endpoint requests processed by status.",
    ("endpoint", "status"),
)

AI_REQUEST_DURATION_SECONDS = Histogram(
    "ai_request_duration_seconds",
    "AI endpoint request duration in seconds.",
    ("endpoint", "status"),
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0),
)

_metrics_server_started = False


def set_pipeline_status(status: str) -> None:
    """Set the active pipeline status gauge and clear known inactive states."""
    known_statuses = ("healthy", "degraded", "unavailable")
    for known_status in known_statuses:
        PIPELINE_STATUS.labels(status=known_status).set(1.0 if status == known_status else 0.0)
    if status not in known_statuses:
        PIPELINE_STATUS.labels(status=status).set(1.0)


def start_metrics_server(port: int) -> None:
    """Start the Prometheus metrics server once per process."""
    global _metrics_server_started

    if _metrics_server_started:
        return
    start_http_server(port)
    _metrics_server_started = True
    logger.info("metrics.server_started", port=port)
