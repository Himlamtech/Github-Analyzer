"""Prometheus metrics definitions for the GitHub AI Trend Analyzer pipeline.

All metrics are registered as module-level singletons so that any component
that imports this module can record observations without dependency injection.
The HTTP server is started once at application boot.
"""

from __future__ import annotations

import prometheus_client as prom
from prometheus_client import Counter, Gauge, Histogram, start_http_server

# ── GitHub API ────────────────────────────────────────────────────────────────

GITHUB_API_REQUESTS_TOTAL: Counter = prom.Counter(
    "github_api_requests_total",
    "Total number of GitHub API requests made.",
    labelnames=["token_index", "status_code"],
)

GITHUB_API_TOKEN_CONFIGURED_INFO: Gauge = prom.Gauge(
    "github_api_token_configured_info",
    "One gauge series per configured GitHub API token.",
    labelnames=["token_index"],
)

GITHUB_API_RATE_LIMIT_REMAINING: Gauge = prom.Gauge(
    "github_api_rate_limit_remaining",
    "Remaining GitHub API requests before rate limit resets.",
    labelnames=["token_index"],
)

GITHUB_API_RATE_LIMIT_RESET_AT_SECONDS: Gauge = prom.Gauge(
    "github_api_rate_limit_reset_at_seconds",
    "Unix timestamp when the GitHub API token rate limit resets.",
    labelnames=["token_index"],
)

GITHUB_API_TOKEN_EXHAUSTED: Gauge = prom.Gauge(
    "github_api_token_exhausted",
    "Whether a GitHub API token is currently considered exhausted (1) or not (0).",
    labelnames=["token_index"],
)

# ── Kafka ─────────────────────────────────────────────────────────────────────

KAFKA_MESSAGES_PRODUCED_TOTAL: Counter = prom.Counter(
    "kafka_messages_produced_total",
    "Total number of messages successfully produced to Kafka.",
    labelnames=["topic"],
)

KAFKA_PRODUCER_ERROR_TOTAL: Counter = prom.Counter(
    "kafka_producer_error_total",
    "Total number of Kafka producer errors.",
    labelnames=["topic", "error_type"],
)

# ── Pipeline ingestion (used by use case layer) ───────────────────────────────

EVENTS_INGESTED_TOTAL: Counter = prom.Counter(
    "events_ingested_total",
    "Total GitHub events accepted by the poller and published to Kafka.",
)

EVENTS_FILTERED_TOTAL: Counter = prom.Counter(
    "events_filtered_total",
    "Total GitHub events discarded by the poller filter due to invalid shape.",
)

# ── Spark ─────────────────────────────────────────────────────────────────────

SPARK_BATCH_DURATION_SECONDS: Histogram = prom.Histogram(
    "spark_batch_duration_seconds",
    "Duration of each Spark micro-batch in seconds.",
    buckets=[1, 5, 10, 30, 60, 120, 300],
)

SPARK_RECORDS_PROCESSED_TOTAL: Counter = prom.Counter(
    "spark_records_processed_total",
    "Total records written by Spark.",
    labelnames=["sink"],  # "parquet" | "clickhouse"
)

# ── ClickHouse ────────────────────────────────────────────────────────────────

CLICKHOUSE_INSERT_ROWS_TOTAL: Counter = prom.Counter(
    "clickhouse_insert_rows_total",
    "Total rows inserted into ClickHouse.",
)

# ── Data quality ──────────────────────────────────────────────────────────────

DATA_FRESHNESS_SECONDS: Gauge = prom.Gauge(
    "data_freshness_seconds",
    "Seconds since the most recent event was stored in ClickHouse. "
    "Should remain below 300 (5 minutes).",
)

# ── Cron / Poll job tracking ──────────────────────────────────────────────────

POLL_CYCLE_TOTAL: Counter = prom.Counter(
    "poll_cycle_total",
    "Total number of GitHub API poll cycles executed.",
)

POLL_CYCLE_DURATION_SECONDS: Histogram = prom.Histogram(
    "poll_cycle_duration_seconds",
    "Wall-clock duration of one full poll cycle (fetch + filter + publish).",
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
)

POLL_LAST_SUCCESS_TIMESTAMP: Gauge = prom.Gauge(
    "poll_last_success_timestamp_seconds",
    "Unix timestamp of the last successful poll cycle completion.",
)

POLL_BATCH_SIZE: Histogram = prom.Histogram(
    "poll_batch_size_events",
    "Number of raw events received per poll cycle from the GitHub API.",
    buckets=[0, 5, 10, 20, 30, 50, 100],
)

POLL_CONSECUTIVE_ERRORS: Gauge = prom.Gauge(
    "poll_consecutive_errors_total",
    "Number of consecutive poll cycles that ended in an error. Resets to 0 on success.",
)

# ── API request observability ────────────────────────────────────────────────

API_REQUESTS_TOTAL: Counter = prom.Counter(
    "api_requests_total",
    "Total number of HTTP requests handled by the API.",
    labelnames=["method", "route", "status_code"],
)

API_REQUEST_DURATION_SECONDS: Histogram = prom.Histogram(
    "api_request_duration_seconds",
    "Request latency for API endpoints in seconds.",
    labelnames=["method", "route", "status_code"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10, 20, 30],
)

API_IN_FLIGHT_REQUESTS: Gauge = prom.Gauge(
    "api_in_flight_requests",
    "Number of in-flight API requests currently being processed.",
)


def start_metrics_server(port: int = 9091) -> None:
    """Start the Prometheus HTTP exposition server.

    Must be called once at application startup.  Prometheus scrapes
    the ``/metrics`` endpoint on the given port.

    Args:
        port: TCP port for the metrics HTTP server (default: 9091).
    """
    start_http_server(port)
