"""Kafka event producer using aiokafka with orjson serialization.

Design decisions:
- orjson for serialization: 2-5x faster than stdlib json
- lz4 compression: best throughput/latency trade-off for event streams
- acks="all": durability guarantee (waits for all in-sync replicas)
- batch_size=64KB + linger_ms=100: amortise network overhead without sacrificing latency
- Key = repo_id bytes: same repo always routes to the same partition (ordering guarantee)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaConnectionError, KafkaTimeoutError, ProducerClosed
import orjson
import structlog

from src.domain.exceptions import ProducerException
from src.infrastructure.observability.metrics import (
    KAFKA_MESSAGES_PRODUCED_TOTAL,
    KAFKA_PRODUCER_ERROR_TOTAL,
)

logger = structlog.get_logger(__name__)

if TYPE_CHECKING:
    from src.application.dtos.github_event_dto import GithubEventOutputDTO


def _serialize_value(dto: GithubEventOutputDTO) -> bytes:
    """Serialise the output DTO to JSON bytes using orjson.

    Args:
        dto: The event DTO to serialise.

    Returns:
        UTF-8 encoded JSON bytes.
    """
    return orjson.dumps(dto.model_dump())


def _serialize_key(repo_id: int) -> bytes:
    """Serialise repo_id as UTF-8 bytes for Kafka partition key.

    Args:
        repo_id: Integer repository ID.

    Returns:
        UTF-8 encoded repo_id string.
    """
    return str(repo_id).encode("utf-8")


class KafkaEventProducer:
    """Async Kafka producer for GitHub events.

    Wraps ``aiokafka.AIOKafkaProducer`` with domain-specific serialisation
    and error translation.

    Args:
        bootstrap_servers: Comma-separated Kafka broker addresses.
        topic:             Kafka topic to publish events to.
    """

    def __init__(self, bootstrap_servers: str, topic: str) -> None:
        self._bootstrap_servers = bootstrap_servers
        self._topic = topic
        self._producer: AIOKafkaProducer | None = None

    async def start(self) -> None:
        """Initialise and start the underlying aiokafka producer.

        Raises:
            ProducerException: If the connection to Kafka fails.
        """
        try:
            self._producer = AIOKafkaProducer(
                bootstrap_servers=self._bootstrap_servers,
                acks="all",
                compression_type="gzip",
                max_batch_size=65536,
                linger_ms=100,
                max_request_size=52428800,  # 50 MB (repo metadata + README + all issues)
                request_timeout_ms=30000,
            )
            await self._producer.start()
            logger.info("kafka_producer.started", topic=self._topic)
        except KafkaConnectionError as exc:
            raise ProducerException(
                f"Failed to connect to Kafka at {self._bootstrap_servers}: {exc}"
            ) from exc

    async def stop(self) -> None:
        """Flush all buffered messages and shut down the producer."""
        if self._producer is not None:
            await self._producer.stop()
            self._producer = None
            logger.info("kafka_producer.stopped", topic=self._topic)

    async def publish(self, event: GithubEventOutputDTO) -> None:
        """Publish a single GitHub event to the Kafka topic.

        Args:
            event: The serialisable output DTO to publish.

        Raises:
            ProducerException: If the producer is not started or publish fails.
        """
        if self._producer is None:
            raise ProducerException(
                "KafkaEventProducer.start() must be called before publish()."
            )

        key = _serialize_key(event.repo_id)
        value = _serialize_value(event)

        try:
            await self._producer.send_and_wait(
                self._topic,
                key=key,
                value=value,
            )
            KAFKA_MESSAGES_PRODUCED_TOTAL.labels(topic=self._topic).inc()
            logger.debug(
                "kafka_producer.published",
                topic=self._topic,
                event_id=event.event_id,
                repo_name=event.repo_name,
            )
        except KafkaTimeoutError as exc:
            KAFKA_PRODUCER_ERROR_TOTAL.labels(
                topic=self._topic, error_type="timeout"
            ).inc()
            raise ProducerException(
                f"Kafka publish timed out for event {event.event_id}: {exc}"
            ) from exc
        except ProducerClosed as exc:
            KAFKA_PRODUCER_ERROR_TOTAL.labels(
                topic=self._topic, error_type="producer_closed"
            ).inc()
            raise ProducerException(
                f"Kafka producer was closed while publishing event {event.event_id}: {exc}"
            ) from exc
