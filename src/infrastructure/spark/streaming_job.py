"""Spark Structured Streaming job: Kafka → Parquet + ClickHouse.

Architecture:
- Single Kafka readStream, two independent write streams (dual sink pattern)
- Parquet sink: append mode, partitioned by event_date + event_type
- ClickHouse sink: foreachBatch, bulk INSERT via JDBC
- Watermark: 10 minutes — allows late data before state is finalised
- Trigger: 60-second micro-batches (configurable)
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from pyspark.sql import DataFrame, SparkSession, functions
import structlog

from src.infrastructure.observability.metrics import (
    SPARK_BATCH_DURATION_SECONDS,
    SPARK_RECORDS_PROCESSED_TOTAL,
)
from src.infrastructure.spark.schemas import GITHUB_EVENT_SCHEMA

logger = structlog.get_logger(__name__)

if TYPE_CHECKING:
    from src.infrastructure.config import Settings

StreamingQuery = Any

_CLICKHOUSE_INSERT_CHUNK_SIZE = 1_000


class GithubStreamingJob:
    """Manages the Spark Structured Streaming pipeline.

    Reads raw JSON events from Kafka, parses them using the explicit schema,
    and fans out to two sinks: Parquet archive and ClickHouse analytical store.

    Args:
        spark:    A configured SparkSession (from session_factory).
        settings: Application settings (duck-typed for testability).
    """

    def __init__(self, spark: SparkSession, settings: object) -> None:
        self._spark = spark
        self._cfg: Settings = settings  # type: ignore[assignment]
        self._parquet_query: StreamingQuery | None = None
        self._clickhouse_query: StreamingQuery | None = None

    def start(self) -> None:
        """Build and start both streaming sinks.

        Raises:
            Exception: If Spark fails to start the streaming queries.
        """
        raw_stream = self._build_kafka_source()
        parsed = self._parse_events(raw_stream)

        self._parquet_query = self._build_parquet_sink(parsed)
        self._clickhouse_query = self._build_clickhouse_sink(parsed)

        logger.info(
            "spark_streaming_job.started",
            parquet_query_id=self._parquet_query.id,
            clickhouse_query_id=self._clickhouse_query.id,
        )

    def await_termination(self) -> None:
        """Block the calling thread until all streaming queries terminate."""
        if self._parquet_query is not None:
            self._parquet_query.awaitTermination()
        if self._clickhouse_query is not None:
            self._clickhouse_query.awaitTermination()

    def stop(self) -> None:
        """Gracefully stop all running streaming queries."""
        for query in (self._parquet_query, self._clickhouse_query):
            if query is not None and query.isActive:
                query.stop()
                logger.info("spark_streaming_job.query_stopped", query_id=query.id)

    def _build_kafka_source(self) -> DataFrame:
        """Configure the Kafka readStream.

        Returns:
            A streaming DataFrame with raw ``key`` and ``value`` columns.
        """
        return (
            self._spark.readStream.format("kafka")
            .option("kafka.bootstrap.servers", self._cfg.kafka_bootstrap_servers)
            .option("subscribe", self._cfg.kafka_topic)
            .option("startingOffsets", "latest")
            .option("failOnDataLoss", "false")
            .option("maxOffsetsPerTrigger", 50000)
            .option("kafka.max.partition.fetch.bytes", 52428800)
            .load()
            .select(
                functions.col("key").cast("string").alias("key"),
                functions.col("value").cast("string").alias("value"),
            )
        )

    def _parse_events(self, raw: DataFrame) -> DataFrame:
        """Parse JSON values from Kafka into typed columns.

        Applies a watermark on ``created_at`` for stateful aggregations.

        Args:
            raw: Streaming DataFrame with raw ``value`` JSON strings.

        Returns:
            Typed streaming DataFrame with all event fields plus ``event_date``.
        """
        parsed = raw.select(
            functions.from_json(functions.col("value"), GITHUB_EVENT_SCHEMA).alias("data")
        ).select("data.*")

        return parsed.withColumn(
            "created_at",
            functions.to_timestamp(functions.col("created_at"), "yyyy-MM-dd'T'HH:mm:ssXXX"),
        ).withWatermark("created_at", "10 minutes")

    def _build_parquet_sink(self, parsed: DataFrame) -> StreamingQuery:
        """Build the Parquet write stream.

        Partitions output by ``event_date`` and ``event_type`` for efficient
        DuckDB partition pruning.

        Args:
            parsed: Typed streaming DataFrame.

        Returns:
            The started Parquet StreamingQuery.
        """
        return (
            parsed.writeStream.format("parquet")
            .option("path", self._cfg.parquet_base_path)
            .option(
                "checkpointLocation",
                f"{self._cfg.checkpoint_base_path}/parquet",
            )
            .partitionBy("event_date", "event_type")
            .trigger(processingTime="60 seconds")
            .outputMode("append")
            .start()
        )

    def _build_clickhouse_sink(self, parsed: DataFrame) -> StreamingQuery:
        """Build the ClickHouse foreachBatch write stream.

        Uses ``foreachBatch`` (not a native connector) because the open-source
        ClickHouse driver works in batch mode. Each micro-batch is streamed to
        the driver in bounded chunks so the pipeline does not materialise the
        full batch in memory before inserting.

        Args:
            parsed: Typed streaming DataFrame.

        Returns:
            The started ClickHouse StreamingQuery.
        """
        cfg = self._cfg

        def write_batch(batch_df: DataFrame, batch_id: int) -> None:
            """Write a single micro-batch to ClickHouse via JDBC."""
            t_start = time.monotonic()

            try:
                import clickhouse_driver

                normalized_batch = batch_df.select(
                    "event_id",
                    "event_type",
                    "actor_id",
                    "actor_login",
                    "repo_id",
                    "repo_name",
                    "created_at",
                    "payload_json",
                    functions.coalesce(
                        functions.col("repo_stargazers_count").cast("long"), functions.lit(0)
                    ).alias("repo_stargazers_count"),
                    functions.coalesce(
                        functions.col("repo_primary_language"), functions.lit("")
                    ).alias("repo_primary_language"),
                    functions.when(
                        functions.col("repo_topics").isNull(),
                        functions.array().cast("array<string>"),
                    )
                    .otherwise(functions.col("repo_topics"))
                    .alias("repo_topics"),
                    functions.coalesce(functions.col("repo_description"), functions.lit("")).alias(
                        "repo_description"
                    ),
                    functions.coalesce(
                        functions.col("repo_full_metadata_json"), functions.lit("")
                    ).alias("repo_full_metadata_json"),
                    functions.coalesce(functions.col("repo_readme_text"), functions.lit("")).alias(
                        "repo_readme_text"
                    ),
                    functions.coalesce(functions.col("repo_issues_json"), functions.lit("")).alias(
                        "repo_issues_json"
                    ),
                )

                client = clickhouse_driver.Client(
                    host=cfg.clickhouse_host,
                    port=cfg.clickhouse_port,
                    user=cfg.clickhouse_user,
                    password=cfg.clickhouse_password,
                    database=cfg.clickhouse_database,
                )
                row_count = 0
                pending_rows: list[tuple[object, ...]] = []

                for row in normalized_batch.toLocalIterator():
                    pending_rows.append(
                        (
                            row["event_id"],
                            row["event_type"],
                            row["actor_id"],
                            row["actor_login"],
                            row["repo_id"],
                            row["repo_name"],
                            row["created_at"],
                            row["payload_json"],
                            row["repo_stargazers_count"],
                            row["repo_primary_language"],
                            row["repo_topics"],
                            row["repo_description"],
                            row["repo_full_metadata_json"],
                            row["repo_readme_text"],
                            row["repo_issues_json"],
                        )
                    )
                    row_count += 1

                    if len(pending_rows) < _CLICKHOUSE_INSERT_CHUNK_SIZE:
                        continue

                    client.execute(
                        "INSERT INTO github_data "
                        "(event_id, event_type, actor_id, actor_login, "
                        "repo_id, repo_name, created_at, payload_json, "
                        "repo_stargazers_count, repo_primary_language, repo_topics, "
                        "repo_description, repo_full_metadata_json, repo_readme_text, "
                        "repo_issues_json) VALUES",
                        pending_rows,
                    )
                    pending_rows = []

                if row_count == 0:
                    return

                if pending_rows:
                    client.execute(
                        "INSERT INTO github_data "
                        "(event_id, event_type, actor_id, actor_login, "
                        "repo_id, repo_name, created_at, payload_json, "
                        "repo_stargazers_count, repo_primary_language, repo_topics, "
                        "repo_description, repo_full_metadata_json, repo_readme_text, "
                        "repo_issues_json) VALUES",
                        pending_rows,
                    )

                elapsed = time.monotonic() - t_start
                SPARK_BATCH_DURATION_SECONDS.observe(elapsed)
                SPARK_RECORDS_PROCESSED_TOTAL.labels(sink="clickhouse").inc(row_count)

                logger.info(
                    "spark_streaming_job.clickhouse_batch_written",
                    batch_id=batch_id,
                    rows=row_count,
                    elapsed_seconds=round(elapsed, 2),
                )
            except Exception as exc:
                logger.error(
                    "spark_streaming_job.clickhouse_batch_failed",
                    batch_id=batch_id,
                    error=str(exc),
                )
                raise

        return (
            parsed.writeStream.foreachBatch(write_batch)
            .option(
                "checkpointLocation",
                f"{self._cfg.checkpoint_base_path}/clickhouse",
            )
            .trigger(processingTime="60 seconds")
            .start()
        )
