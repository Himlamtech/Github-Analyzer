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
        source_type="rss",
        event_type="launch",
        linked_entities=("OpenAI",),
        linked_categories=("Coding Agents & Automation",),
        linked_repo_full_names=("browser-use/browser-use",),
        linked_framework_ids=("browser-use", "openai-agents"),
        quality_score=88.0,
        is_quarantined=False,
        quarantine_reason=None,
    )

    with patch.object(repository, "_get_client", return_value=client):
        count = await repository.upsert_items([item])

    assert count == 1
    assert client.execute.call_count == 3
    assert "CREATE TABLE IF NOT EXISTS external_news_items" in str(
        client.execute.call_args_list[0].args[0]
    )
    assert "linked_entities" in str(client.execute.call_args_list[2].args[0])
    inserted_row = client.execute.call_args_list[2].args[1][0]
    assert inserted_row[7] == "launch"
    assert inserted_row[8] == ["OpenAI"]
    assert inserted_row[10] == ["browser-use/browser-use"]


async def test_list_latest_items_returns_enriched_rows() -> None:
    repository = _make_repository()
    client = MagicMock()
    client.execute.side_effect = [
        None,
        None,
        [
            (
                "openai-1",
                "OpenAI",
                "Launch",
                "https://example.com/launch",
                datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
                "Launch summary.",
                "rss",
                "launch",
                ["OpenAI"],
                ["Coding Agents & Automation"],
                ["browser-use/browser-use"],
                ["browser-use", "openai-agents"],
                88.0,
                0,
                None,
            )
        ],
    ]

    with patch.object(repository, "_get_client", return_value=client):
        rows = await repository.list_latest_items(provider=None, limit=10)

    assert rows[0]["source_id"] == "openai-1"
    assert rows[0]["event_type"] == "launch"
    assert rows[0]["linked_entities"] == ["OpenAI"]
    assert rows[0]["linked_repo_full_names"] == ["browser-use/browser-use"]


async def test_get_item_by_source_id_returns_parsed_row() -> None:
    repository = _make_repository()
    client = MagicMock()
    client.execute.side_effect = [
        None,
        None,
        [
            (
                "openai-1",
                "OpenAI",
                "Launch",
                "https://example.com/launch",
                datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
                "Launch summary.",
                "rss",
                "launch",
                ["OpenAI"],
                ["Coding Agents & Automation"],
                ["browser-use/browser-use"],
                ["browser-use", "openai-agents"],
                88.0,
                0,
                None,
            )
        ],
    ]

    with patch.object(repository, "_get_client", return_value=client):
        row = await repository.get_item_by_source_id("openai-1")

    assert row is not None
    assert row["source_id"] == "openai-1"
    assert row["quality_score"] == 88.0
    assert row["linked_framework_ids"] == ["browser-use", "openai-agents"]


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
    query_text = str(client.execute.call_args_list[2].args[0])
    assert "FROM\n(\n    SELECT" in query_text
    assert "max(checked_at) AS checked_at" in query_text
