"""Spark batch job: Parquet → aggregated ClickHouse tables.

Reads the raw Parquet archive and computes:
1. ``repo_star_counts``: daily star (WatchEvent) delta per repo
2. ``repo_activity_summary``: weekly aggregated event counts per repo

Designed to run periodically (e.g., nightly) or after backfill operations.
"""

from __future__ import annotations

from datetime import UTC, date, timedelta
import time
from typing import TYPE_CHECKING, cast

import pyspark.sql.functions as spark_fn
import structlog

from src.infrastructure.observability.metrics import (
    CLICKHOUSE_INSERT_ROWS_TOTAL,
    SPARK_BATCH_DURATION_SECONDS,
    SPARK_RECORDS_PROCESSED_TOTAL,
)

if TYPE_CHECKING:
    from pyspark.sql import DataFrame, SparkSession

    from src.infrastructure.config import Settings

logger = structlog.get_logger(__name__)


class GithubBatchJob:
    """Reads Parquet and writes aggregated summaries to ClickHouse.

    Args:
        spark:    A configured SparkSession.
        settings: Application settings (duck-typed for testability).
    """

    def __init__(self, spark: SparkSession, settings: object) -> None:
        self._spark = spark
        self._cfg: Settings = cast("Settings", settings)

    def run(
        self,
        lookback_days: int = 7,
        reference_date: date | None = None,
    ) -> None:
        """Execute the full aggregation pipeline.

        Args:
            lookback_days:   Number of days back to aggregate (default: 7).
            reference_date:  End date for the window (default: today UTC).
        """
        if reference_date is None:
            from datetime import datetime

            reference_date = datetime.now(tz=UTC).date()

        start_date = reference_date - timedelta(days=lookback_days)
        logger.info(
            "github_batch_job.started",
            start_date=str(start_date),
            end_date=str(reference_date),
        )
        t_start = time.monotonic()

        raw_df = self._read_parquet(start_date, reference_date)
        self._write_star_counts(raw_df)
        self._write_activity_summary(raw_df)

        elapsed = time.monotonic() - t_start
        SPARK_BATCH_DURATION_SECONDS.observe(elapsed)
        logger.info("github_batch_job.completed", elapsed_seconds=round(elapsed, 2))

    def _read_parquet(self, start_date: date, end_date: date) -> DataFrame:
        """Read Parquet partitions for the given date range.

        Args:
            start_date: Inclusive lower bound.
            end_date:   Inclusive upper bound.

        Returns:
            DataFrame with all events in the requested window.
        """
        # Generate date strings for partition pruning
        dates: list[str] = []
        current = start_date
        while current <= end_date:
            dates.append(current.strftime("%Y-%m-%d"))
            current += timedelta(days=1)

        parquet_paths = [f"{self._cfg.parquet_base_path}/event_date={d}" for d in dates]

        return (
            self._spark.read.format("parquet")
            .option("basePath", self._cfg.parquet_base_path)
            .load(*parquet_paths)
            .withColumn(
                "created_at",
                spark_fn.to_timestamp(spark_fn.col("created_at")),
            )
        )

    def _write_star_counts(self, df: DataFrame) -> None:
        """Compute and write daily star counts (WatchEvents) to ClickHouse.

        Args:
            df: Input events DataFrame.
        """
        star_df = (
            df.filter(spark_fn.col("event_type") == "WatchEvent")
            .groupBy("repo_name", "event_date")
            .agg(spark_fn.count("*").alias("star_count"))
            .withColumn("updated_at", spark_fn.current_timestamp())
        )

        row_count = star_df.count()
        self._jdbc_write(star_df, "repo_star_counts")
        SPARK_RECORDS_PROCESSED_TOTAL.labels(sink="clickhouse").inc(row_count)
        CLICKHOUSE_INSERT_ROWS_TOTAL.inc(row_count)
        logger.info("github_batch_job.star_counts_written", rows=row_count)

    def _write_activity_summary(self, df: DataFrame) -> None:
        """Compute and write weekly activity summaries to ClickHouse.

        Args:
            df: Input events DataFrame.
        """
        summary_df = (
            df.groupBy("repo_name", "event_type")
            .agg(
                spark_fn.count("*").alias("event_count"),
                spark_fn.countDistinct("actor_id").alias("unique_actors"),
                spark_fn.min("created_at").alias("first_seen_at"),
                spark_fn.max("created_at").alias("last_seen_at"),
            )
            .withColumn("computed_at", spark_fn.current_timestamp())
        )

        row_count = summary_df.count()
        self._jdbc_write(summary_df, "repo_activity_summary")
        SPARK_RECORDS_PROCESSED_TOTAL.labels(sink="clickhouse").inc(row_count)
        CLICKHOUSE_INSERT_ROWS_TOTAL.inc(row_count)
        logger.info("github_batch_job.activity_summary_written", rows=row_count)

    def _jdbc_write(self, df: DataFrame, table: str) -> None:
        """Write a DataFrame to a ClickHouse table via JDBC.

        Args:
            df:    DataFrame to write.
            table: Target ClickHouse table name.
        """
        jdbc_url = (
            f"jdbc:clickhouse://{self._cfg.clickhouse_host}:{self._cfg.clickhouse_port}"
            f"/{self._cfg.clickhouse_database}"
        )
        (
            df.write.format("jdbc")
            .option("url", jdbc_url)
            .option("dbtable", table)
            .option("user", self._cfg.clickhouse_user)
            .option("password", self._cfg.clickhouse_password)
            .option("driver", "com.clickhouse.jdbc.ClickHouseDriver")
            .option("batchsize", 10000)
            .option("numPartitions", 4)
            .mode("append")
            .save()
        )
