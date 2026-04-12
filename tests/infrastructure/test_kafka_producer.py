"""Unit tests for KafkaEventProducer — aiokafka is fully mocked."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.application.dtos.github_event_dto import GithubEventOutputDTO
from src.domain.exceptions import ProducerException
from src.infrastructure.kafka.producer import KafkaEventProducer


@pytest.fixture
def output_dto() -> GithubEventOutputDTO:
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


@pytest.fixture
def producer() -> KafkaEventProducer:
    return KafkaEventProducer(
        bootstrap_servers="localhost:9092",
        topic="github_raw_events",
    )


class TestKafkaEventProducerStart:
    """Tests for producer startup."""

    async def test_start_creates_aiokafka_producer(
        self, producer: KafkaEventProducer
    ) -> None:
        """start() must initialise the internal AIOKafkaProducer."""
        mock_inner = AsyncMock()
        with patch(
            "src.infrastructure.kafka.producer.AIOKafkaProducer",
            return_value=mock_inner,
        ):
            await producer.start()
            mock_inner.start.assert_called_once()

    async def test_publish_before_start_raises_producer_exception(
        self,
        producer: KafkaEventProducer,
        output_dto: GithubEventOutputDTO,
    ) -> None:
        """publish() without calling start() first must raise ProducerException."""
        with pytest.raises(ProducerException, match="start\\(\\)"):
            await producer.publish(output_dto)


class TestKafkaEventProducerPublish:
    """Tests for successful publish and error scenarios."""

    async def test_publish_calls_send_and_wait(
        self,
        producer: KafkaEventProducer,
        output_dto: GithubEventOutputDTO,
    ) -> None:
        """Happy path: publish() must call send_and_wait on the inner producer."""
        mock_inner = AsyncMock()
        with patch(
            "src.infrastructure.kafka.producer.AIOKafkaProducer",
            return_value=mock_inner,
        ):
            await producer.start()
            await producer.publish(output_dto)
            mock_inner.send_and_wait.assert_called_once()

    async def test_publish_uses_repo_id_as_key(
        self,
        producer: KafkaEventProducer,
        output_dto: GithubEventOutputDTO,
    ) -> None:
        """publish() must use repo_id bytes as the Kafka partition key."""
        mock_inner = AsyncMock()
        with patch(
            "src.infrastructure.kafka.producer.AIOKafkaProducer",
            return_value=mock_inner,
        ):
            await producer.start()
            await producer.publish(output_dto)
            call_kwargs = mock_inner.send_and_wait.call_args
            assert call_kwargs.kwargs["key"] == b"1234"

    async def test_stop_calls_inner_stop(
        self, producer: KafkaEventProducer
    ) -> None:
        """stop() must flush and close the inner producer."""
        mock_inner = AsyncMock()
        with patch(
            "src.infrastructure.kafka.producer.AIOKafkaProducer",
            return_value=mock_inner,
        ):
            await producer.start()
            await producer.stop()
            mock_inner.stop.assert_called_once()
