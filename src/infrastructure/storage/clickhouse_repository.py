"""ClickHouse event repository used by API diagnostics."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

from clickhouse_driver import Client
from clickhouse_driver.errors import Error as ClickHouseError
from clickhouse_driver.errors import NetworkError as ClickHouseNetworkError


class ClickHouseEventRepository:
    """Small ClickHouse adapter for operational event checks."""

    def __init__(
        self,
        *,
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
        return Client(
            host=self._host,
            port=self._port,
            user=self._user,
            password=self._password,
            database=self._database,
            connect_timeout=5,
            send_receive_timeout=10,
            sync_request_timeout=5,
            settings={"use_client_time_zone": True},
        )

    def _get_max_created_at_sync(self) -> datetime | None:
        try:
            rows = self._get_client().execute("SELECT max(created_at) FROM github_data")
        except (ClickHouseError, ClickHouseNetworkError) as exc:
            raise RuntimeError(f"ClickHouse freshness query failed: {exc}") from exc
        if not rows or rows[0][0] is None:
            return None
        return _coerce_datetime(rows[0][0])

    async def get_max_created_at(self) -> datetime | None:
        """Return the latest event timestamp from ClickHouse."""
        return await asyncio.to_thread(self._get_max_created_at_sync)


def _coerce_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    return datetime.now(tz=UTC)
