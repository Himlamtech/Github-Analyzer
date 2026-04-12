"""PollGithubEventsUseCase — orchestrates the ingestion pipeline.

Responsibility: poll the GitHub Events API, keep every structurally valid
repository event, and publish accepted events to Kafka. No business logic lives
here — it delegates to the domain entity, filter, mapper, and Kafka producer.

This is the entry point for ``make stream``.
"""

from __future__ import annotations

import asyncio
import signal
import time
from typing import TYPE_CHECKING, Protocol

import structlog

from src.domain.exceptions import (
    GitHubAPIError,
    KafkaError,
    RateLimitExceededError,
    ValidationError,
)
from src.infrastructure.observability.metrics import (
    EVENTS_FILTERED_TOTAL,
    EVENTS_INGESTED_TOTAL,
    POLL_BATCH_SIZE,
    POLL_CONSECUTIVE_ERRORS,
    POLL_CYCLE_DURATION_SECONDS,
    POLL_CYCLE_TOTAL,
    POLL_LAST_SUCCESS_TIMESTAMP,
)

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from src.application.dtos.github_event_dto import GithubEventInputDTO, GithubEventOutputDTO
    from src.domain.entities.github_event import GithubEvent

logger = structlog.get_logger(__name__)


class GitHubClientProtocol(Protocol):
    """Minimal interface required from the GitHub client."""

    def stream_events(self) -> AsyncGenerator[list[dict[str, object]], None]: ...


class EventFilterProtocol(Protocol):
    """Minimal interface required from the event filter."""

    def is_ai_relevant(self, event: dict[str, object]) -> bool: ...


class EventMapperProtocol(Protocol):
    """Minimal interface required from the event mapper."""

    def to_input_dto(self, raw: dict[str, object]) -> GithubEventInputDTO: ...

    def to_domain_entity(self, dto: GithubEventInputDTO) -> GithubEvent: ...

    def to_output_dto(self, entity: GithubEvent) -> GithubEventOutputDTO: ...


class KafkaProducerProtocol(Protocol):
    """Minimal interface required from the Kafka producer."""

    async def publish(self, event: GithubEventOutputDTO) -> None: ...

    async def start(self) -> None: ...

    async def stop(self) -> None: ...


class PollGithubEventsUseCase:
    """Continuously polls GitHub, filters, and publishes to Kafka.

    Design: single public ``execute()`` coroutine that runs until cancelled.
    SIGINT/SIGTERM trigger graceful shutdown via ``asyncio.Event``.

    Args:
        github_client:  Async HTTP client for the GitHub Events API.
        event_filter:   Determines whether a raw event is valid for ingestion.
        event_mapper:   Translates raw dicts ↔ DTOs ↔ domain entities.
        kafka_producer: Publishes serialised events to the Kafka topic.
        poll_interval:  Seconds to sleep between API pages (rate-limit friendly).
    """

    def __init__(
        self,
        github_client: GitHubClientProtocol,
        event_filter: EventFilterProtocol,
        event_mapper: EventMapperProtocol,
        kafka_producer: KafkaProducerProtocol,
        poll_interval: float = 2.0,
    ) -> None:
        self._client = github_client
        self._filter = event_filter
        self._mapper = event_mapper
        self._producer = kafka_producer
        self._poll_interval = poll_interval
        self._shutdown_event = asyncio.Event()

    async def execute(self) -> None:
        """Run the ingestion loop until shutdown is signalled.

        Registers SIGINT and SIGTERM handlers so that ``Ctrl+C`` or
        ``docker stop`` triggers a clean producer flush before exit.
        """
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, self._shutdown_event.set)

        await self._producer.start()
        logger.info("poll_github_events.started")

        try:
            async for raw_events in self._client.stream_events():
                if self._shutdown_event.is_set():
                    break
                cycle_start = time.monotonic()
                try:
                    POLL_BATCH_SIZE.observe(len(raw_events))
                    await self._process_batch(raw_events)
                    POLL_CYCLE_TOTAL.inc()
                    POLL_LAST_SUCCESS_TIMESTAMP.set(time.time())
                    POLL_CONSECUTIVE_ERRORS.set(0)
                except (KafkaError, ValidationError) as exc:
                    POLL_CONSECUTIVE_ERRORS.inc()
                    logger.error("poll_github_events.cycle_error", error=str(exc))
                finally:
                    POLL_CYCLE_DURATION_SECONDS.observe(time.monotonic() - cycle_start)
                await asyncio.sleep(self._poll_interval)
        except RateLimitExceededError as exc:
            logger.warning(
                "poll_github_events.rate_limit_exhausted",
                reset_in=exc.reset_at_seconds,
            )
            await asyncio.sleep(exc.reset_at_seconds)
        except GitHubAPIError as exc:
            POLL_CONSECUTIVE_ERRORS.inc()
            logger.error("poll_github_events.github_api_error", error=str(exc))
        except KafkaError as exc:
            logger.error("poll_github_events.kafka_error", error=str(exc))
        finally:
            await self._producer.stop()
            logger.info("poll_github_events.stopped")

    async def _process_batch(self, raw_events: list[dict[str, object]]) -> None:
        """Filter and publish a single batch of raw API events.

        Args:
            raw_events: List of raw GitHub event dicts from one API page.
        """
        published_count = 0
        filtered_count = 0
        validation_error_count = 0
        publish_error_count = 0

        for raw in raw_events:
            if not self._filter.is_ai_relevant(raw):
                EVENTS_FILTERED_TOTAL.inc()
                filtered_count += 1
                continue

            try:
                dto = self._mapper.to_input_dto(raw)
                entity = self._mapper.to_domain_entity(dto)
            except ValidationError as exc:
                validation_error_count += 1
                logger.warning(
                    "poll_github_events.validation_error",
                    error=str(exc),
                    event_id=raw.get("id"),
                )
                continue

            output_dto = self._mapper.to_output_dto(entity)

            try:
                await self._producer.publish(output_dto)
                EVENTS_INGESTED_TOTAL.inc()
                published_count += 1
                logger.debug(
                    "poll_github_events.published",
                    event_id=entity.event_id,
                    repo=str(entity.repo_id),
                    event_type=str(entity.event_type),
                )
            except KafkaError as exc:
                publish_error_count += 1
                logger.error(
                    "poll_github_events.publish_failed",
                    event_id=entity.event_id,
                    error=str(exc),
                )

        logger.info(
            "poll_github_events.batch_processed",
            raw_event_count=len(raw_events),
            published_count=published_count,
            filtered_count=filtered_count,
            validation_error_count=validation_error_count,
            publish_error_count=publish_error_count,
        )


async def _main() -> None:
    """Composition root for standalone execution via ``make stream``."""
    from src.infrastructure.config import get_settings
    from src.infrastructure.github.client import GitHubClient
    from src.infrastructure.github.event_filter import PopularRepoFilter
    from src.infrastructure.github.event_mapper import GitHubEventMapper
    from src.infrastructure.kafka.producer import KafkaEventProducer
    from src.infrastructure.kafka.topic_admin import KafkaTopicAdmin
    from src.infrastructure.observability.logging_config import configure_logging

    settings = get_settings()
    configure_logging(settings.log_level)

    from src.infrastructure.observability.metrics import start_metrics_server

    start_metrics_server(settings.metrics_port)

    topic_admin = KafkaTopicAdmin(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        retention_hours=settings.kafka_retention_hours,
    )
    await topic_admin.ensure_topic(settings.kafka_topic)

    github_client = GitHubClient(
        tokens=settings.github_tokens_list,
        base_url=str(settings.github_api_base_url),
    )
    event_filter = PopularRepoFilter()
    event_mapper = GitHubEventMapper()
    kafka_producer = KafkaEventProducer(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        topic=settings.kafka_topic,
    )

    use_case = PollGithubEventsUseCase(
        github_client=github_client,
        event_filter=event_filter,
        event_mapper=event_mapper,
        kafka_producer=kafka_producer,
        poll_interval=settings.poll_interval_seconds,
    )
    await use_case.execute()


if __name__ == "__main__":
    asyncio.run(_main())
