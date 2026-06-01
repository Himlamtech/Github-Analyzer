"""ClickHouse-backed persistence for external news items and source health."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import TYPE_CHECKING, Any, cast

from clickhouse_driver import Client
from clickhouse_driver.errors import Error as ClickHouseError
from clickhouse_driver.errors import NetworkError as ClickHouseNetworkError
import structlog

from src.domain.exceptions import ClickHouseConnectionError, ClickHouseWriteError
from src.domain.repositories.external_news_repository import ExternalNewsRepositoryABC

if TYPE_CHECKING:
    from src.domain.entities.external_news_item import ExternalNewsItem

logger = structlog.get_logger(__name__)

_CREATE_EXTERNAL_NEWS_ITEMS_TABLE_QUERY = """
CREATE TABLE IF NOT EXISTS external_news_items
(
    source_id String,
    provider LowCardinality(String),
    title String,
    url String,
    published_at DateTime('UTC'),
    summary String,
    source_type LowCardinality(String),
    event_type LowCardinality(String),
    linked_entities Array(String),
    linked_categories Array(String),
    linked_repo_full_names Array(String),
    linked_framework_ids Array(String),
    quality_score Float64,
    is_quarantined UInt8,
    quarantine_reason Nullable(String),
    ingested_at DateTime('UTC')
)
ENGINE = ReplacingMergeTree(ingested_at)
PARTITION BY toYYYYMM(published_at)
ORDER BY (provider, source_id)
SETTINGS index_granularity = 8192
"""

_INSERT_EXTERNAL_NEWS_ITEMS_QUERY = """
INSERT INTO external_news_items
(
    source_id,
    provider,
    title,
    url,
    published_at,
    summary,
    source_type,
    event_type,
    linked_entities,
    linked_categories,
    linked_repo_full_names,
    linked_framework_ids,
    quality_score,
    is_quarantined,
    quarantine_reason,
    ingested_at
)
VALUES
"""

_CREATE_SOURCE_HEALTH_TABLE_QUERY = """
CREATE TABLE IF NOT EXISTS source_health_snapshots
(
    provider LowCardinality(String),
    source_url String,
    status LowCardinality(String),
    fetched_count Int64,
    error_message Nullable(String),
    checked_at DateTime('UTC')
)
ENGINE = ReplacingMergeTree(checked_at)
PARTITION BY toYYYYMM(checked_at)
ORDER BY (provider, source_url, checked_at)
SETTINGS index_granularity = 8192
"""

_INSERT_SOURCE_HEALTH_QUERY = """
INSERT INTO source_health_snapshots
(provider, source_url, status, fetched_count, error_message, checked_at)
VALUES
"""

_SELECT_LATEST_ITEMS_QUERY = """
SELECT
    source_id,
    provider,
    title,
    url,
    published_at,
    summary,
    source_type,
    event_type,
    linked_entities,
    linked_categories,
    linked_repo_full_names,
    linked_framework_ids,
    quality_score,
    is_quarantined,
    quarantine_reason
FROM external_news_items
FINAL
{where_clause}
ORDER BY published_at DESC, provider ASC
LIMIT %(limit)s
"""

_SELECT_ITEM_BY_SOURCE_ID_QUERY = """
SELECT
    source_id,
    provider,
    title,
    url,
    published_at,
    summary,
    source_type,
    event_type,
    linked_entities,
    linked_categories,
    linked_repo_full_names,
    linked_framework_ids,
    quality_score,
    is_quarantined,
    quarantine_reason
FROM external_news_items
FINAL
WHERE source_id = %(source_id)s
ORDER BY published_at DESC
LIMIT 1
"""

_SELECT_LATEST_SOURCE_HEALTH_QUERY = """
SELECT
    provider,
    source_url,
    status,
    fetched_count,
    error_message,
    latest_checked_at AS checked_at
FROM
(
    SELECT
        provider,
        source_url,
        argMax(status, checked_at) AS status,
        argMax(fetched_count, checked_at) AS fetched_count,
        argMax(error_message, checked_at) AS error_message,
        max(checked_at) AS latest_checked_at
    FROM source_health_snapshots
    GROUP BY provider, source_url
)
ORDER BY provider ASC, source_url ASC
"""


class ClickHouseExternalNewsRepository(ExternalNewsRepositoryABC):
    """Persist external news items and source health snapshots into ClickHouse."""

    def __init__(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        database: str,
    ) -> None:
        self._host = host
        self._port = port
        self._user = user
        self._password = password
        self._database = database

    def _get_client(self) -> Client:
        try:
            return Client(
                host=self._host,
                port=self._port,
                user=self._user,
                password=self._password,
                database=self._database,
                connect_timeout=10,
                send_receive_timeout=30,
                sync_request_timeout=5,
                settings={"use_client_time_zone": True},
            )
        except ClickHouseNetworkError as exc:
            raise ClickHouseConnectionError(
                f"Cannot connect to ClickHouse at {self._host}:{self._port}: {exc}"
            ) from exc

    def _execute(self, client: Client, query: str, rows: list[tuple[Any, ...]]) -> None:
        try:
            client.execute(query, rows)
        except ClickHouseError as exc:
            raise ClickHouseWriteError(f"ClickHouse insert error: {exc}") from exc

    @staticmethod
    def _item_to_row(item: ExternalNewsItem, ingested_at: datetime) -> tuple[Any, ...]:
        return (
            item.source_id,
            item.provider,
            item.title,
            item.url,
            item.published_at,
            item.summary,
            item.source_type,
            item.event_type,
            list(item.linked_entities),
            list(item.linked_categories),
            list(item.linked_repo_full_names),
            list(item.linked_framework_ids),
            item.quality_score,
            int(item.is_quarantined),
            item.quarantine_reason,
            ingested_at,
        )

    def _ensure_tables(self, client: Client) -> None:
        client.execute(_CREATE_EXTERNAL_NEWS_ITEMS_TABLE_QUERY)
        client.execute(_CREATE_SOURCE_HEALTH_TABLE_QUERY)

    async def upsert_items(self, items: list[ExternalNewsItem]) -> int:
        if not items:
            return 0

        def _write() -> int:
            client = self._get_client()
            self._ensure_tables(client)
            ingested_at = datetime.utcnow()
            rows = [self._item_to_row(item, ingested_at) for item in items]
            self._execute(client, _INSERT_EXTERNAL_NEWS_ITEMS_QUERY, rows)
            return len(rows)

        return await asyncio.to_thread(_write)

    async def append_source_health_snapshot(
        self,
        *,
        provider: str,
        source_url: str,
        status: str,
        fetched_count: int,
        error_message: str | None,
        checked_at: datetime,
    ) -> None:
        def _write() -> None:
            client = self._get_client()
            self._ensure_tables(client)
            self._execute(
                client,
                _INSERT_SOURCE_HEALTH_QUERY,
                [(provider, source_url, status, fetched_count, error_message, checked_at)],
            )

        await asyncio.to_thread(_write)

    async def list_latest_items(
        self,
        *,
        provider: str | None,
        limit: int,
        include_quarantined: bool = False,
    ) -> list[dict[str, object]]:
        where_parts: list[str] = []
        if provider:
            where_parts.append("provider = %(provider)s")
        if not include_quarantined:
            where_parts.append("is_quarantined = 0")
        where_clause = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""
        query = _SELECT_LATEST_ITEMS_QUERY.format(where_clause=where_clause)
        params: dict[str, object] = {"limit": limit}
        if provider:
            params["provider"] = provider

        def _query() -> list[tuple[object, ...]]:
            client = self._get_client()
            self._ensure_tables(client)
            return cast("list[tuple[object, ...]]", client.execute(query, params))

        rows = await asyncio.to_thread(_query)
        return [
            {
                "source_id": row[0],
                "provider": row[1],
                "title": row[2],
                "url": row[3],
                "published_at": row[4],
                "summary": row[5],
                "source_type": row[6],
                "event_type": row[7],
                "linked_entities": row[8],
                "linked_categories": row[9],
                "linked_repo_full_names": row[10],
                "linked_framework_ids": row[11],
                "quality_score": row[12],
                "is_quarantined": bool(row[13]),
                "quarantine_reason": row[14],
            }
            for row in rows
        ]

    async def get_item_by_source_id(self, source_id: str) -> dict[str, object] | None:
        def _query() -> list[tuple[object, ...]]:
            client = self._get_client()
            self._ensure_tables(client)
            return cast(
                "list[tuple[object, ...]]",
                client.execute(_SELECT_ITEM_BY_SOURCE_ID_QUERY, {"source_id": source_id}),
            )

        rows = await asyncio.to_thread(_query)
        if not rows:
            return None

        row = rows[0]
        return {
            "source_id": row[0],
            "provider": row[1],
            "title": row[2],
            "url": row[3],
            "published_at": row[4],
            "summary": row[5],
            "source_type": row[6],
            "event_type": row[7],
            "linked_entities": row[8],
            "linked_categories": row[9],
            "linked_repo_full_names": row[10],
            "linked_framework_ids": row[11],
            "quality_score": row[12],
            "is_quarantined": bool(row[13]),
            "quarantine_reason": row[14],
        }

    async def list_latest_source_health(self) -> list[dict[str, object]]:
        def _query() -> list[tuple[object, ...]]:
            client = self._get_client()
            self._ensure_tables(client)
            return cast(
                "list[tuple[object, ...]]",
                client.execute(_SELECT_LATEST_SOURCE_HEALTH_QUERY),
            )

        rows = await asyncio.to_thread(_query)
        return [
            {
                "provider": row[0],
                "source_url": row[1],
                "status": row[2],
                "fetched_count": row[3],
                "error_message": row[4],
                "checked_at": row[5],
            }
            for row in rows
        ]
