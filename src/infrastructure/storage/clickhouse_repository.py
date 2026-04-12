"""ClickHouse-backed implementation of EventRepositoryABC.

Uses ``clickhouse-driver`` (sync) wrapped in ``asyncio.to_thread`` for
non-blocking operation in the async application layer.

Tables targeted:
    github_data  — MergeTree, partitioned by toYYYYMM(created_at)
"""

from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime
from typing import TYPE_CHECKING, cast

from clickhouse_driver import Client
from clickhouse_driver.errors import Error as ClickHouseError
from clickhouse_driver.errors import NetworkError as ClickHouseNetworkError
import structlog

from src.domain.entities.github_event import GithubEvent
from src.domain.exceptions import (
    ClickHouseConnectionError,
    ClickHouseWriteError,
)
from src.domain.repositories.event_repository import EventRepositoryABC
from src.infrastructure.observability.metrics import CLICKHOUSE_INSERT_ROWS_TOTAL

logger = structlog.get_logger(__name__)

if TYPE_CHECKING:
    from src.domain.value_objects.repository_id import RepositoryId

_BATCH_SIZE = 10_000
_INSERT_EVENTS_QUERY = """
INSERT INTO github_data
(event_id, event_type, actor_id, actor_login, repo_id, repo_name, created_at, payload_json,
 repo_stargazers_count, repo_primary_language, repo_topics, repo_description,
 repo_full_metadata_json, repo_readme_text, repo_issues_json)
VALUES
"""


class ClickHouseEventRepository(EventRepositoryABC):
    """Persists GithubEvent aggregates to ClickHouse.

    Args:
        host:     ClickHouse server hostname.
        port:     Native TCP protocol port (default: 9000).
        user:     ClickHouse username.
        password: ClickHouse password.
        database: Target database name.
    """

    @staticmethod
    def _as_string_list(value: object) -> list[str]:
        if not isinstance(value, list):
            return []
        return [str(item) for item in value]

    @staticmethod
    def _as_int(value: object) -> int:
        return int(cast("int | float | str", value or 0))

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
        """Create a new ClickHouse client connection.

        Each call creates a fresh connection.  For long-lived services,
        consider a connection pool — but for batch inserts the overhead
        is negligible.

        Returns:
            A connected ClickHouse Client.

        Raises:
            ClickHouseConnectionError: If the connection cannot be established.
        """
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

    def _entity_to_row(self, entity: GithubEvent) -> tuple[object, ...]:
        """Convert a domain entity to a ClickHouse INSERT row tuple.

        Args:
            entity: GithubEvent aggregate root.

        Returns:
            Tuple matching the INSERT column order.
        """
        import orjson

        return (
            entity.event_id,
            str(entity.event_type),
            entity.actor_id,
            entity.actor_login,
            entity.repo_id.value,
            str(entity.repo_id),
            entity.created_at,
            orjson.dumps(entity.payload).decode(),
            self._as_int(entity.payload.get("_repo_stargazers_count", 0)),
            str(entity.payload.get("_repo_primary_language", "") or ""),
            self._as_string_list(entity.payload.get("_repo_topics", [])),
            str(entity.payload.get("_repo_description", "") or ""),
            str(entity.payload.get("_repo_full_metadata_json", "") or ""),
            str(entity.payload.get("_repo_readme_text", "") or ""),
            str(entity.payload.get("_repo_issues_json", "") or ""),
        )

    def _execute_bulk_insert(
        self, client: Client, query: str, rows: list[tuple[object, ...]]
    ) -> None:
        """Execute a bulk INSERT with retry on network errors.

        Args:
            client: Active ClickHouse client.
            query:  INSERT INTO ... VALUES query string.
            rows:   List of row tuples.

        Raises:
            ClickHouseWriteError: If the insert fails after retries.
        """
        import time

        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                client.execute(query, rows)
                return
            except ClickHouseNetworkError as exc:
                if attempt == max_attempts:
                    raise ClickHouseWriteError(
                        f"ClickHouse bulk insert failed after {max_attempts} attempts: {exc}"
                    ) from exc
                backoff = 2 ** (attempt - 1)
                logger.warning(
                    "clickhouse_repository.retry",
                    attempt=attempt,
                    backoff=backoff,
                    error=str(exc),
                )
                time.sleep(backoff)
            except ClickHouseError as exc:
                raise ClickHouseWriteError(
                    f"ClickHouse insert error: {exc}"
                ) from exc

    async def save(self, event: GithubEvent) -> None:
        """Persist a single GithubEvent to ClickHouse.

        Args:
            event: The aggregate to store.
        """
        await self.save_batch([event])

    async def save_batch(self, events: list[GithubEvent]) -> None:
        """Persist a batch of GithubEvent aggregates.

        Splits large batches into chunks of ``_BATCH_SIZE`` to stay within
        ClickHouse's recommended insert size.

        Args:
            events: List of aggregates to store.
        """
        if not events:
            return

        rows = [self._entity_to_row(e) for e in events]

        def _write() -> None:
            client = self._get_client()
            for i in range(0, len(rows), _BATCH_SIZE):
                chunk = rows[i : i + _BATCH_SIZE]
                self._execute_bulk_insert(client, _INSERT_EVENTS_QUERY, chunk)
                CLICKHOUSE_INSERT_ROWS_TOTAL.inc(len(chunk))
                logger.debug(
                    "clickhouse_repository.batch_written",
                    rows=len(chunk),
                    offset=i,
                )

        await asyncio.to_thread(_write)

    async def find_by_repo(
        self, repo_id: RepositoryId, limit: int = 100
    ) -> list[GithubEvent]:
        """Return events for a specific repository, most recent first.

        Args:
            repo_id: Target repository identity.
            limit:   Maximum number of events to return.

        Returns:
            Ordered list of GithubEvent instances.
        """
        query = """
        SELECT event_id, event_type, actor_id, actor_login,
               repo_id, repo_name, created_at, payload_json, 1 as public
        FROM github_data
        WHERE repo_id = %(repo_id)s
        ORDER BY created_at DESC
        LIMIT %(limit)s
        """
        params: dict[str, object] = {"repo_id": repo_id.value, "limit": limit}

        def _query() -> list[tuple[object, ...]]:
            client = self._get_client()
            return cast("list[tuple[object, ...]]", client.execute(query, params))

        rows = await asyncio.to_thread(_query)
        return [self._row_to_entity(row) for row in rows]

    async def find_by_date_range(
        self,
        start: date,
        end: date,
        limit: int = 1000,
    ) -> list[GithubEvent]:
        """Return events within the given UTC date range.

        Args:
            start:  Inclusive lower bound.
            end:    Inclusive upper bound.
            limit:  Maximum number of events to return.

        Returns:
            Ordered list of GithubEvent instances.
        """
        query = """
        SELECT event_id, event_type, actor_id, actor_login,
               repo_id, repo_name, created_at, payload_json, 1 as public
        FROM github_data
        WHERE created_at >= %(start)s AND created_at <= %(end)s
        ORDER BY created_at DESC
        LIMIT %(limit)s
        """
        start_dt = datetime.combine(start, datetime.min.time()).replace(tzinfo=UTC)
        end_dt = datetime.combine(end, datetime.max.time()).replace(tzinfo=UTC)
        params: dict[str, object] = {"start": start_dt, "end": end_dt, "limit": limit}

        def _query() -> list[tuple[object, ...]]:
            client = self._get_client()
            return cast("list[tuple[object, ...]]", client.execute(query, params))

        rows = await asyncio.to_thread(_query)
        return [self._row_to_entity(row) for row in rows]

    async def get_max_created_at(self) -> float | None:
        """Return the Unix timestamp of the most recent stored event.

        Returns:
            Unix epoch float, or None if the table is empty.
        """
        query = "SELECT toUnixTimestamp(max(created_at)) FROM github_data"

        def _query() -> list[tuple[object, ...]]:
            client = self._get_client()
            return cast("list[tuple[object, ...]]", client.execute(query))

        rows = await asyncio.to_thread(_query)
        if rows and rows[0][0]:
            return float(cast("float | int | str", rows[0][0]))
        return None

    def _row_to_entity(self, row: tuple[object, ...]) -> GithubEvent:
        """Convert a ClickHouse SELECT row to a GithubEvent entity.

        Args:
            row: Tuple matching the SELECT column order in query methods.

        Returns:
            Reconstructed GithubEvent aggregate root.
        """
        import orjson

        from src.domain.value_objects.event_type import EventType
        from src.domain.value_objects.repository_id import RepositoryId

        (
            event_id,
            event_type_str,
            actor_id,
            actor_login,
            repo_id_int,
            repo_name,
            created_at,
            payload_json,
            _public,
        ) = row

        created_at_dt: datetime = created_at  # type: ignore[assignment]
        if created_at_dt.tzinfo is None:
            created_at_dt = created_at_dt.replace(tzinfo=UTC)

        payload: dict[str, object] = {}
        if payload_json:
            payload = orjson.loads(str(payload_json))

        return GithubEvent(
            event_id=str(event_id),
            event_type=EventType.from_raw(str(event_type_str)),
            repo_id=RepositoryId.from_api(
                repo_id=int(str(repo_id_int)),
                repo_name=str(repo_name),
            ),
            actor_id=int(str(actor_id)),
            actor_login=str(actor_login),
            created_at=created_at_dt,
            payload=payload,
            public=True,
        )
