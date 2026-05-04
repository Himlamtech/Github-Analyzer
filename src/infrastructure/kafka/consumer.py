"""Kafka event consumer using aiokafka.

Provides an async generator interface over raw Kafka messages.
Deserialises messages from orjson bytes back to Python dicts.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaConnectionError, KafkaError
import orjson
import structlog

from src.domain.exceptions import ConsumerException

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

logger = structlog.get_logger(__name__)


class KafkaEventConsumer:
    """Async Kafka consumer that yields deserialised event dicts.

    Designed for integration testing and non-Spark consumers.
    The primary production consumer is Spark Structured Streaming
    (which manages its own Kafka consumer group internally).

    Args:
        bootstrap_servers: Comma-separated Kafka broker addresses.
        topic:             Kafka topic to consume from.
        group_id:          Consumer group ID for offset tracking.
        auto_offset_reset: Where to start if no committed offset exists.
                           "latest" for live processing, "earliest" for replay.
    """

    def __init__(
        self,
        bootstrap_servers: str,
        topic: str,
        group_id: str = "github_analyzer_consumer",
        auto_offset_reset: str = "latest",
    ) -> None:
        self._bootstrap_servers = bootstrap_servers
        self._topic = topic
        self._group_id = group_id
        self._auto_offset_reset = auto_offset_reset
        self._consumer: AIOKafkaConsumer | None = None

    async def start(self) -> None:
        """Initialise and start the underlying aiokafka consumer.

        Raises:
            ConsumerException: If the connection to Kafka fails.
        """
        try:
            self._consumer = AIOKafkaConsumer(
                self._topic,
                bootstrap_servers=self._bootstrap_servers,
                group_id=self._group_id,
                auto_offset_reset=self._auto_offset_reset,
                enable_auto_commit=True,
                auto_commit_interval_ms=5000,
                max_poll_records=500,
            )
            await self._consumer.start()
            logger.info(
                "kafka_consumer.started",
                topic=self._topic,
                group_id=self._group_id,
            )
        except KafkaConnectionError as exc:
            raise ConsumerException(
                f"Failed to connect to Kafka at {self._bootstrap_servers}: {exc}"
            ) from exc

    async def stop(self) -> None:
        """Commit offsets and shut down the consumer."""
        if self._consumer is not None:
            await self._consumer.stop()
            self._consumer = None
            logger.info("kafka_consumer.stopped", topic=self._topic)

    async def consume(self) -> AsyncGenerator[dict[str, object], None]:
        """Async generator that yields one deserialised event dict per message.

        Yields:
            Deserialised event dict from Kafka message value.

        Raises:
            ConsumerException: If the consumer is not started or a fatal error occurs.
        """
        if self._consumer is None:
            raise ConsumerException("KafkaEventConsumer.start() must be called before consume().")

        try:
            async for msg in self._consumer:
                if msg.value is None:
                    continue
                try:
                    event_dict: dict[str, object] = orjson.loads(msg.value)
                    yield event_dict
                except orjson.JSONDecodeError as exc:
                    logger.warning(
                        "kafka_consumer.deserialization_error",
                        offset=msg.offset,
                        partition=msg.partition,
                        error=str(exc),
                    )
                    continue
        except KafkaError as exc:
            raise ConsumerException(f"Kafka consumer error: {exc}") from exc
