"""Explicit PySpark StructType schemas for all Spark jobs.

Rationale for explicit schemas (no inferSchema):
- Avoids full-scan of Parquet files at job startup (expensive for large archives)
- Guarantees type safety — no silent coercions from string to numeric
- Required when reading from Kafka (raw bytes have no schema)
- Enables schema evolution tracking via code review
"""

from __future__ import annotations

from pyspark.sql.types import (
    ArrayType,
    BooleanType,
    IntegerType,
    LongType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)

# ── Kafka message schema ──────────────────────────────────────────────────────
# The Kafka source always produces: key (bytes), value (bytes), topic, partition,
# offset, timestamp, timestampType.  We only need key and value.
KAFKA_RAW_SCHEMA: StructType = StructType(
    [
        StructField("key", StringType(), nullable=True),
        StructField("value", StringType(), nullable=False),
    ]
)

# ── GitHub event schema (parsed from JSON in Kafka value) ─────────────────────
GITHUB_EVENT_SCHEMA: StructType = StructType(
    [
        StructField("event_id", StringType(), nullable=False),
        StructField("event_type", StringType(), nullable=False),
        StructField("actor_id", LongType(), nullable=False),
        StructField("actor_login", StringType(), nullable=False),
        StructField("repo_id", LongType(), nullable=False),
        StructField("repo_name", StringType(), nullable=False),
        StructField("event_date", StringType(), nullable=False),
        StructField("created_at", StringType(), nullable=False),
        StructField("payload_json", StringType(), nullable=True),
        StructField("repo_stargazers_count", LongType(), nullable=True),
        StructField("repo_primary_language", StringType(), nullable=True),
        StructField("repo_topics", ArrayType(StringType()), nullable=True),
        StructField("repo_description", StringType(), nullable=True),
        StructField("repo_full_metadata_json", StringType(), nullable=True),
        StructField("repo_readme_text", StringType(), nullable=True),
        StructField("repo_issues_json", StringType(), nullable=True),
        StructField("public", BooleanType(), nullable=True),
    ]
)

# ── Parquet output schema (enriched with parsed timestamp) ────────────────────
PARQUET_EVENT_SCHEMA: StructType = StructType(
    [
        StructField("event_id", StringType(), nullable=False),
        StructField("event_type", StringType(), nullable=False),
        StructField("actor_id", LongType(), nullable=False),
        StructField("actor_login", StringType(), nullable=False),
        StructField("repo_id", LongType(), nullable=False),
        StructField("repo_name", StringType(), nullable=False),
        StructField("created_at", TimestampType(), nullable=False),
        StructField("payload_json", StringType(), nullable=True),
        StructField("repo_stargazers_count", LongType(), nullable=True),
        StructField("repo_primary_language", StringType(), nullable=True),
        StructField("repo_topics", ArrayType(StringType()), nullable=True),
        StructField("repo_description", StringType(), nullable=True),
        StructField("repo_full_metadata_json", StringType(), nullable=True),
        StructField("repo_readme_text", StringType(), nullable=True),
        StructField("repo_issues_json", StringType(), nullable=True),
        StructField("public", BooleanType(), nullable=True),
        # Partition columns — written as directory names, not data columns
        StructField("event_date", StringType(), nullable=False),
    ]
)

# ── Window aggregation schema (tumbling 1-hour windows) ──────────────────────
WINDOW_AGG_SCHEMA: StructType = StructType(
    [
        StructField("window_start", TimestampType(), nullable=False),
        StructField("window_end", TimestampType(), nullable=False),
        StructField("repo_name", StringType(), nullable=False),
        StructField("event_type", StringType(), nullable=False),
        StructField("event_count", IntegerType(), nullable=False),
    ]
)

# ── ClickHouse github_data table schema ──────────────────────────────────────
CLICKHOUSE_EVENT_SCHEMA: StructType = StructType(
    [
        StructField("event_id", StringType(), nullable=False),
        StructField("event_type", StringType(), nullable=False),
        StructField("actor_id", LongType(), nullable=False),
        StructField("actor_login", StringType(), nullable=False),
        StructField("repo_id", LongType(), nullable=False),
        StructField("repo_name", StringType(), nullable=False),
        StructField("created_at", TimestampType(), nullable=False),
        StructField("payload_json", StringType(), nullable=True),
        StructField("repo_stargazers_count", LongType(), nullable=True),
        StructField("repo_primary_language", StringType(), nullable=True),
        StructField("repo_topics", ArrayType(StringType()), nullable=True),
        StructField("repo_description", StringType(), nullable=True),
        StructField("repo_full_metadata_json", StringType(), nullable=True),
        StructField("repo_readme_text", StringType(), nullable=True),
        StructField("repo_issues_json", StringType(), nullable=True),
    ]
)
