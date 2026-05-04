"""Kafka topic administration — idempotent topic creation on startup.

Uses aiokafka's admin client to verify or create the ``github_raw_events``
topic before any producer or consumer attempts to use it.
"""

from __future__ import annotations

from aiokafka.admin import AIOKafkaAdminClient, NewTopic
from aiokafka.errors import KafkaConnectionError, TopicAlreadyExistsError
import structlog

from src.domain.exceptions import TopicAdminException

logger = structlog.get_logger(__name__)


class KafkaTopicAdmin:
    """Idempotent Kafka topic manager.

    Args:
        bootstrap_servers: Comma-separated Kafka broker addresses.
        retention_hours:   Log retention window in hours (default: 168 = 7 days).
    """

    def __init__(
        self,
        bootstrap_servers: str,
        retention_hours: int = 168,
    ) -> None:
        self._bootstrap_servers = bootstrap_servers
        self._retention_ms = str(retention_hours * 3_600_000)

    async def ensure_topic(
        self,
        topic: str,
        num_partitions: int = 16,
        replication_factor: int = 1,
    ) -> None:
        """Create the Kafka topic if it does not already exist.

        This method is idempotent: if the topic already exists with
        compatible settings, it succeeds silently.

        Args:
            topic:              Topic name.
            num_partitions:     Number of partitions (default: 16).
            replication_factor: Replication factor (default: 1 for local dev).

        Raises:
            TopicAdminException: If the Kafka admin operation fails unexpectedly.
        """
        admin: AIOKafkaAdminClient | None = None
        try:
            admin = AIOKafkaAdminClient(bootstrap_servers=self._bootstrap_servers)
            await admin.start()

            new_topic = NewTopic(
                name=topic,
                num_partitions=num_partitions,
                replication_factor=replication_factor,
                topic_configs={"retention.ms": self._retention_ms},
            )
            await admin.create_topics([new_topic])
            logger.info(
                "kafka_topic_admin.topic_created",
                topic=topic,
                partitions=num_partitions,
            )
        except TopicAlreadyExistsError:
            logger.info("kafka_topic_admin.topic_already_exists", topic=topic)
        except KafkaConnectionError as exc:
            raise TopicAdminException(
                f"Cannot connect to Kafka at {self._bootstrap_servers}: {exc}"
            ) from exc
        except Exception as exc:
            raise TopicAdminException(f"Failed to create Kafka topic {topic!r}: {exc}") from exc
        finally:
            if admin is not None:
                await admin.close()
