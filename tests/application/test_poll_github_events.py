"""Unit tests for PollGithubEventsUseCase.

All external dependencies (GitHub client, filter, mapper, Kafka producer)
are mocked — no real network calls or Kafka connections are made.
"""

from __future__ import annotations

from datetime import UTC, datetime
import sys
from types import ModuleType, SimpleNamespace
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.application.dtos.github_event_dto import GithubEventInputDTO, GithubEventOutputDTO
from src.application.use_cases.poll_github_events import PollGithubEventsUseCase, _main
from src.domain.entities.github_event import GithubEvent
from src.domain.exceptions import (
    GitHubAPIError,
    ProducerException,
    RateLimitExceededError,
    ValidationError,
)
from src.domain.value_objects.event_type import EventType
from src.domain.value_objects.repository_id import RepositoryId

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


def _make_output_dto() -> GithubEventOutputDTO:
    return GithubEventOutputDTO(
        event_id="evt_001",
        event_type="WatchEvent",
        actor_id=999,
        actor_login="researcher",
        repo_id=1234,
        repo_name="openai/gpt-5",
        event_date="2024-06-15",
        created_at="2024-06-15T12:00:00+00:00",
        payload_json="{}",
    )


def _make_domain_entity() -> GithubEvent:
    return GithubEvent(
        event_id="evt_001",
        event_type=EventType.WATCH,
        repo_id=RepositoryId.from_api(1234, "openai/gpt-5"),
        actor_id=999,
        actor_login="researcher",
        created_at=datetime(2024, 6, 15, 12, tzinfo=UTC),
    )


def _make_input_dto() -> GithubEventInputDTO:
    return GithubEventInputDTO(
        event_id="evt_001",
        event_type="WatchEvent",
        actor_id=999,
        actor_login="researcher",
        repo_id=1234,
        repo_name="openai/gpt-5",
        created_at=datetime(2024, 6, 15, 12, tzinfo=UTC),
    )


@pytest.fixture
def mock_raw_event() -> dict[str, object]:
    return {
        "id": "evt_001",
        "type": "WatchEvent",
        "actor": {"id": 999, "login": "researcher"},
        "repo": {"id": 1234, "name": "openai/gpt-5"},
        "payload": {},
        "created_at": "2024-06-15T12:00:00Z",
        "public": True,
    }


@pytest.fixture
def mock_github_client(mock_raw_event: dict[str, object]) -> MagicMock:
    """Mock GitHub client that yields one batch then raises StopAsyncIteration."""

    async def _stream() -> AsyncGenerator[list[dict[str, object]], None]:
        yield [mock_raw_event]

    client = MagicMock()
    client.stream_events = _stream
    return client


@pytest.fixture
def mock_filter() -> MagicMock:
    filt = MagicMock()
    filt.is_ai_relevant.return_value = True
    return filt


@pytest.fixture
def mock_mapper() -> MagicMock:
    mapper = MagicMock()
    mapper.to_input_dto.return_value = _make_input_dto()
    mapper.to_domain_entity.return_value = _make_domain_entity()
    mapper.to_output_dto.return_value = _make_output_dto()
    return mapper


@pytest.fixture
def mock_producer() -> AsyncMock:
    producer = AsyncMock()
    producer.start = AsyncMock()
    producer.stop = AsyncMock()
    producer.publish = AsyncMock()
    return producer


@pytest.fixture
def use_case(
    mock_github_client: MagicMock,
    mock_filter: MagicMock,
    mock_mapper: MagicMock,
    mock_producer: AsyncMock,
) -> PollGithubEventsUseCase:
    return PollGithubEventsUseCase(
        github_client=mock_github_client,
        event_filter=mock_filter,
        event_mapper=mock_mapper,
        kafka_producer=mock_producer,
        poll_interval=0.0,  # No sleep in tests
    )


class TestPollGithubEventsUseCaseHappyPath:
    """Tests for normal execution flow."""

    async def test_execute_publishes_ai_relevant_event(
        self,
        use_case: PollGithubEventsUseCase,
        mock_producer: AsyncMock,
    ) -> None:
        """Happy path: AI-relevant event is published to Kafka exactly once."""
        await use_case.execute()
        mock_producer.publish.assert_called_once()

    async def test_execute_calls_producer_start_and_stop(
        self,
        use_case: PollGithubEventsUseCase,
        mock_producer: AsyncMock,
    ) -> None:
        """The producer start() and stop() must both be called."""
        await use_case.execute()
        mock_producer.start.assert_called_once()
        mock_producer.stop.assert_called_once()


class TestPollGithubEventsUseCaseFiltering:
    """Tests for filter integration."""

    async def test_filtered_event_is_not_published(
        self,
        mock_github_client: MagicMock,
        mock_filter: MagicMock,
        mock_mapper: MagicMock,
        mock_producer: AsyncMock,
    ) -> None:
        """Events rejected by the filter must not reach Kafka."""
        mock_filter.is_ai_relevant.return_value = False
        uc = PollGithubEventsUseCase(
            github_client=mock_github_client,
            event_filter=mock_filter,
            event_mapper=mock_mapper,
            kafka_producer=mock_producer,
            poll_interval=0.0,
        )
        await uc.execute()
        mock_producer.publish.assert_not_called()


class TestPollGithubEventsUseCaseErrorHandling:
    """Tests for error path handling."""

    async def test_validation_error_skips_event_does_not_raise(
        self,
        mock_github_client: MagicMock,
        mock_filter: MagicMock,
        mock_mapper: MagicMock,
        mock_producer: AsyncMock,
    ) -> None:
        """ValidationError during mapping must be logged and skipped, not propagated."""
        mock_mapper.to_input_dto.side_effect = ValidationError("bad event")
        uc = PollGithubEventsUseCase(
            github_client=mock_github_client,
            event_filter=mock_filter,
            event_mapper=mock_mapper,
            kafka_producer=mock_producer,
            poll_interval=0.0,
        )
        # Should complete without raising
        await uc.execute()
        mock_producer.publish.assert_not_called()

    async def test_kafka_error_during_publish_is_logged(
        self,
        mock_github_client: MagicMock,
        mock_filter: MagicMock,
        mock_mapper: MagicMock,
        mock_producer: AsyncMock,
    ) -> None:
        """ProducerException during publish must not crash the use case."""
        mock_producer.publish.side_effect = ProducerException("kafka down")
        uc = PollGithubEventsUseCase(
            github_client=mock_github_client,
            event_filter=mock_filter,
            event_mapper=mock_mapper,
            kafka_producer=mock_producer,
            poll_interval=0.0,
        )
        # Should not raise
        await uc.execute()

    async def test_rate_limit_error_sleeps_then_stops_producer(
        self,
        mock_filter: MagicMock,
        mock_mapper: MagicMock,
        mock_producer: AsyncMock,
    ) -> None:
        """Rate-limit exhaustion must sleep until reset and still stop the producer."""

        async def _stream() -> AsyncGenerator[list[dict[str, object]], None]:
            raise RateLimitExceededError(reset_at_seconds=3.0)
            yield []

        client = MagicMock()
        client.stream_events = _stream
        uc = PollGithubEventsUseCase(
            github_client=client,
            event_filter=mock_filter,
            event_mapper=mock_mapper,
            kafka_producer=mock_producer,
            poll_interval=0.0,
        )

        with patch(
            "src.application.use_cases.poll_github_events.asyncio.sleep",
            new=AsyncMock(),
        ) as sleep_mock:
            await uc.execute()

        sleep_mock.assert_awaited_once_with(3.0)
        mock_producer.stop.assert_awaited_once()

    async def test_github_api_error_is_swallowed_and_stops_producer(
        self,
        mock_filter: MagicMock,
        mock_mapper: MagicMock,
        mock_producer: AsyncMock,
    ) -> None:
        """Unexpected GitHub API failures must not leak past execute()."""

        async def _stream() -> AsyncGenerator[list[dict[str, object]], None]:
            raise GitHubAPIError("upstream down")
            yield []

        client = MagicMock()
        client.stream_events = _stream
        uc = PollGithubEventsUseCase(
            github_client=client,
            event_filter=mock_filter,
            event_mapper=mock_mapper,
            kafka_producer=mock_producer,
            poll_interval=0.0,
        )

        await uc.execute()

        mock_producer.stop.assert_awaited_once()

    async def test_shutdown_event_breaks_before_processing_batch(
        self,
        mock_github_client: MagicMock,
        mock_filter: MagicMock,
        mock_mapper: MagicMock,
        mock_producer: AsyncMock,
    ) -> None:
        """When shutdown is already set, the next batch should be skipped entirely."""
        uc = PollGithubEventsUseCase(
            github_client=mock_github_client,
            event_filter=mock_filter,
            event_mapper=mock_mapper,
            kafka_producer=mock_producer,
            poll_interval=0.0,
        )
        uc._shutdown_event.set()

        await uc.execute()

        mock_producer.publish.assert_not_awaited()


@pytest.mark.asyncio
async def test_main_wires_dependencies_and_executes_use_case() -> None:
    settings = SimpleNamespace(
        log_level="INFO",
        metrics_port=9091,
        kafka_bootstrap_servers="localhost:9092",
        kafka_retention_hours=168,
        kafka_topic="github_raw_events",
        github_tokens_list=["token-a", "token-b"],
        github_api_base_url="https://api.github.com",
        poll_interval_seconds=0.5,
    )
    execute_mock = AsyncMock()
    ensure_topic_mock = AsyncMock()
    topic_admin_instances: list[object] = []
    github_client_instances: list[object] = []
    producer_instances: list[object] = []

    config_module = ModuleType("src.infrastructure.config")
    config_module.get_settings = lambda: settings  # type: ignore[attr-defined]

    logging_module = ModuleType("src.infrastructure.observability.logging_config")
    logging_module.configure_logging = lambda level: None  # type: ignore[attr-defined]

    metrics_module = ModuleType("src.infrastructure.observability.metrics")
    metrics_module.start_metrics_server = lambda port: None  # type: ignore[attr-defined]

    github_client_module = ModuleType("src.infrastructure.github.client")

    class FakeGitHubClient:
        def __init__(self, *, tokens: list[str], base_url: str) -> None:
            self.tokens = tokens
            self.base_url = base_url
            github_client_instances.append(self)

    github_client_module.GitHubClient = FakeGitHubClient  # type: ignore[attr-defined]

    filter_module = ModuleType("src.infrastructure.github.event_filter")
    filter_module.PopularRepoFilter = type("PopularRepoFilter", (), {})  # type: ignore[attr-defined]

    mapper_module = ModuleType("src.infrastructure.github.event_mapper")
    mapper_module.GitHubEventMapper = type("GitHubEventMapper", (), {})  # type: ignore[attr-defined]

    producer_module = ModuleType("src.infrastructure.kafka.producer")

    class FakeKafkaEventProducer:
        def __init__(self, *, bootstrap_servers: str, topic: str) -> None:
            self.bootstrap_servers = bootstrap_servers
            self.topic = topic
            producer_instances.append(self)

    producer_module.KafkaEventProducer = FakeKafkaEventProducer  # type: ignore[attr-defined]

    topic_admin_module = ModuleType("src.infrastructure.kafka.topic_admin")

    class FakeKafkaTopicAdmin:
        def __init__(self, *, bootstrap_servers: str, retention_hours: int) -> None:
            self.bootstrap_servers = bootstrap_servers
            self.retention_hours = retention_hours
            self.ensure_topic = ensure_topic_mock
            topic_admin_instances.append(self)

    topic_admin_module.KafkaTopicAdmin = FakeKafkaTopicAdmin  # type: ignore[attr-defined]

    with (
        patch.dict(
            sys.modules,
            {
                "src.infrastructure.config": config_module,
                "src.infrastructure.observability.logging_config": logging_module,
                "src.infrastructure.observability.metrics": metrics_module,
                "src.infrastructure.github.client": github_client_module,
                "src.infrastructure.github.event_filter": filter_module,
                "src.infrastructure.github.event_mapper": mapper_module,
                "src.infrastructure.kafka.producer": producer_module,
                "src.infrastructure.kafka.topic_admin": topic_admin_module,
            },
        ),
        patch.object(PollGithubEventsUseCase, "execute", execute_mock),
    ):
        await _main()

    ensure_topic_mock.assert_awaited_once_with("github_raw_events")
    execute_mock.assert_awaited_once()
    assert len(topic_admin_instances) == 1
    assert len(github_client_instances) == 1
    assert len(producer_instances) == 1
