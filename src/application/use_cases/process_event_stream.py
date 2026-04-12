"""ProcessEventStreamUseCase — orchestrates the Spark streaming pipeline.

Responsibility: bootstrap the SparkSession, start the structured streaming
job that reads from Kafka and writes to Parquet + ClickHouse, then await
termination.  No Spark-specific logic lives here — it delegates to
``streaming_job.py`` in the Infrastructure layer.

Entry point for ``make process``.
"""

from __future__ import annotations

import asyncio
import signal
from typing import Protocol

import structlog

from src.domain.exceptions import SparkJobError

logger = structlog.get_logger(__name__)


class SparkStreamingJobProtocol(Protocol):
    """Minimal interface required from the Spark streaming infrastructure."""

    def start(self) -> None: ...

    def await_termination(self) -> None: ...

    def stop(self) -> None: ...


class ProcessEventStreamUseCase:
    """Starts and supervises the Spark Structured Streaming pipeline.

    The Spark job blocks ``await_termination()`` internally, so this
    use case wraps it in a thread executor to keep the asyncio event
    loop unblocked and allow graceful shutdown on SIGINT/SIGTERM.

    Args:
        streaming_job: Preconfigured Spark streaming job instance.
    """

    def __init__(self, streaming_job: SparkStreamingJobProtocol) -> None:
        self._job = streaming_job
        self._shutdown_event = asyncio.Event()

    async def execute(self) -> None:
        """Start the Spark streaming job and block until termination.

        Raises:
            SparkJobError: If the job fails to start or encounters a fatal error.
        """
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, self._on_shutdown)

        logger.info("process_event_stream.starting")

        try:
            await loop.run_in_executor(None, self._job.start)
            logger.info("process_event_stream.started")
            await loop.run_in_executor(None, self._job.await_termination)
        except Exception as exc:
            raise SparkJobError(f"Spark streaming job failed: {exc}") from exc
        finally:
            logger.info("process_event_stream.stopping")
            await loop.run_in_executor(None, self._job.stop)
            logger.info("process_event_stream.stopped")

    def _on_shutdown(self) -> None:
        """Signal handler that initiates graceful job termination."""
        logger.info("process_event_stream.shutdown_signal_received")
        self._shutdown_event.set()
        self._job.stop()


async def _main() -> None:
    """Composition root for standalone execution via ``make process``."""
    from src.infrastructure.config import get_settings
    from src.infrastructure.observability.logging_config import configure_logging
    from src.infrastructure.observability.metrics import start_metrics_server
    from src.infrastructure.spark.session_factory import create_spark_session
    from src.infrastructure.spark.streaming_job import GithubStreamingJob

    settings = get_settings()
    configure_logging(settings.log_level)
    start_metrics_server(settings.metrics_port)

    spark = create_spark_session(settings)
    streaming_job = GithubStreamingJob(spark=spark, settings=settings)

    use_case = ProcessEventStreamUseCase(streaming_job=streaming_job)
    await use_case.execute()


if __name__ == "__main__":
    asyncio.run(_main())
