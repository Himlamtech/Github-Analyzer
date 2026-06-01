"""Unit tests for ClickHouseExternalNewsRepository."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from src.domain.entities.external_news_item import ExternalNewsItem
from src.infrastructure.storage.clickhouse_external_news_repository import (
    ClickHouseExternalNewsRepository,
)


def _make_repository() -> ClickHouseExternalNewsRepository:
    return ClickHouseExternalNewsRepository(
        host="localhost",
        port=9000,
        user="default",
        password="secret",
        database="github_analyzer",
    )


async def test_upsert_items_creates_table_and_inserts_rows() -> None:
    repository = _make_repository()
    client = MagicMock()
    item = ExternalNewsItem(
        source_id="openai-1",
        provider="OpenAI",
        title="Launch",
        url="https://example.com/launch",
        published_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        summary="Launch summary.",
    )

    with patch.object(repository, "_get_client", return_value=client):
        count = await repository.upsert_items([item])

    assert count == 1
    assert client.execute.call_count == 3
    assert "CREATE TABLE IF NOT EXISTS external_news_items" in str(
        client.execute.call_args_list[0].args[0]
    )
    assert "INSERT INTO external_news_items" in str(client.execute.call_args_list[2].args[0])


async def test_list_latest_source_health_returns_parsed_rows() -> None:
    repository = _make_repository()
    client = MagicMock()
    client.execute.side_effect = [
        None,
        None,
        [
            (
                "OpenAI",
                "https://openai.com/news/rss.xml",
                "ok",
                3,
                None,
                datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
            )
        ],
    ]

    with patch.object(repository, "_get_client", return_value=client):
        rows = await repository.list_latest_source_health()

    assert rows[0]["provider"] == "OpenAI"
    assert rows[0]["status"] == "ok"
