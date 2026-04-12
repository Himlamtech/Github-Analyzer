"""SparkSession factory — creates a configured SparkSession instance.

Configuration targets the local hardware profile:
- local[16]: uses all 16 performance cores of i7-12700F
- driver 8g / executor 12g: respects ~25GB available RAM budget
- Kryo serializer: 2-4x faster than Java default for binary data
- Kafka integration packages loaded at session creation
"""

from __future__ import annotations

import structlog
from pyspark.sql import SparkSession

logger = structlog.get_logger(__name__)

# Spark packages required at runtime — fetched from Maven on first run
_SPARK_PACKAGES = ",".join(
    [
        "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1",
        "com.clickhouse:clickhouse-jdbc:0.6.0",
        "org.apache.httpcomponents.client5:httpclient5:5.3.1",
    ]
)


def create_spark_session(settings: object) -> SparkSession:
    """Create and return a configured SparkSession.

    This function is idempotent — if a SparkSession already exists with
    the same app name, it returns the existing instance.

    Args:
        settings: Application settings instance (duck-typed for testability).
                  Expected attributes: spark_master, spark_driver_memory,
                  spark_executor_memory.

    Returns:
        A fully configured, started SparkSession.
    """
    from src.infrastructure.config import Settings

    cfg: Settings = settings  # type: ignore[assignment]

    spark = (
        SparkSession.builder.appName("GithubAiTrendAnalyzer")
        .master(cfg.spark_master)
        .config("spark.driver.memory", cfg.spark_driver_memory)
        .config("spark.executor.memory", cfg.spark_executor_memory)
        # Serializer
        .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer")
        .config("spark.kryo.registrationRequired", "false")
        # Kafka integration package
        .config("spark.jars.packages", _SPARK_PACKAGES)
        # SQL optimisations
        .config("spark.sql.adaptive.enabled", "true")
        .config("spark.sql.adaptive.coalescePartitions.enabled", "true")
        .config("spark.sql.shuffle.partitions", "16")
        # Streaming
        .config("spark.sql.streaming.checkpointLocation", "./data/checkpoints/default")
        .config("spark.streaming.stopGracefullyOnShutdown", "true")
        # Parquet
        .config("spark.sql.parquet.compression.codec", "snappy")
        .config("spark.hadoop.mapreduce.fileoutputcommitter.algorithm.version", "2")
        # Reduce excessive INFO logging from Spark internals
        .config("spark.log.level", "WARN")
        .getOrCreate()
    )

    spark.sparkContext.setLogLevel("WARN")
    logger.info(
        "spark_session.created",
        master=cfg.spark_master,
        driver_memory=cfg.spark_driver_memory,
        executor_memory=cfg.spark_executor_memory,
    )
    return spark
