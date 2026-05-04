"""Bootstrap github_data in ClickHouse from the local Parquet archive."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

from clickhouse_driver import Client
from clickhouse_driver.errors import Error as ClickHouseError
from clickhouse_driver.errors import NetworkError as ClickHouseNetworkError
import pyarrow as pa  # type: ignore[import-untyped]
import pyarrow.parquet as pq  # type: ignore[import-untyped]
import structlog

from src.domain.exceptions import (
    ClickHouseBackfillError,
    ClickHouseConnectionError,
)

logger = structlog.get_logger(__name__)

_COUNT_ROWS_QUERY = "SELECT count() FROM github_data"
_TRUNCATE_TABLE_QUERY = "TRUNCATE TABLE github_data"
_INSERT_EVENTS_QUERY = """
INSERT INTO github_data
(event_id, event_type, actor_id, actor_login, repo_id, repo_name, created_at, payload_json,
 repo_stargazers_count, repo_primary_language, repo_topics, repo_description,
 repo_full_metadata_json, repo_readme_text, repo_issues_json)
VALUES
"""


def _as_int(value: object) -> int:
    """Safely coerce a raw record value to int for insertion."""
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int | float | str):
        return int(value)
    return 0


@dataclass(frozen=True)
class ClickHouseBackfillResult:
    """Summary of a completed Parquet-to-ClickHouse bootstrap run."""

    inserted_rows: int
    batch_count: int
    start_date: date | None
    end_date: date | None


class ClickHouseBackfillService:
    """Stream local Parquet events into ClickHouse in bounded batches."""

    def __init__(
        self,
        *,
        host: str,
        port: int,
        user: str,
        password: str,
        database: str,
        parquet_base_path: str,
        batch_size: int = 10_000,
    ) -> None:
        self._host = host
        self._port = port
        self._user = user
        self._password = password
        self._database = database
        self._parquet_base_path = parquet_base_path.rstrip("/")
        self._batch_size = batch_size

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

    def _ensure_parquet_exists(self) -> None:
        base_path = Path(self._parquet_base_path)
        if not base_path.exists() or not any(base_path.glob("event_date=*")):
            raise ClickHouseBackfillError(
                f"No Hive partitions found under parquet base path: {self._parquet_base_path}"
            )

    def _partition_query_paths(
        self,
        *,
        start_date: date | None,
        end_date: date | None,
    ) -> list[str]:
        base_path = Path(self._parquet_base_path)
        partition_dates = sorted(
            path.name.split("=", maxsplit=1)[1]
            for path in base_path.glob("event_date=*")
            if path.is_dir() and "=" in path.name
        )

        start_date_iso = self._optional_date(start_date)
        end_date_iso = self._optional_date(end_date)
        return [
            f"{self._parquet_base_path}/event_date={partition_date}/event_type=*/*.parquet"
            for partition_date in partition_dates
            if (start_date_iso is None or partition_date >= start_date_iso)
            and (end_date_iso is None or partition_date <= end_date_iso)
        ]

    def _partition_files(
        self,
        *,
        start_date: date | None,
        end_date: date | None,
    ) -> list[Path]:
        files: list[Path] = []
        partition_globs = self._partition_query_paths(
            start_date=start_date,
            end_date=end_date,
        )
        for partition_glob in partition_globs:
            partition_path = Path(partition_glob.split("/event_type=", maxsplit=1)[0])
            files.extend(sorted(partition_path.rglob("*.parquet")))
        return files

    @staticmethod
    def _normalize_record(record: dict[str, object]) -> tuple[object, ...]:
        created_at = record.get("created_at")
        created_at_value = (
            created_at.replace(tzinfo=UTC)
            if isinstance(created_at, datetime) and created_at.tzinfo is None
            else created_at
        )
        topics_value = record.get("repo_topics")
        repo_topics = list(topics_value) if isinstance(topics_value, list | tuple) else []
        return (
            str(record.get("event_id") or ""),
            str(record.get("event_type") or ""),
            _as_int(record.get("actor_id")),
            str(record.get("actor_login") or ""),
            _as_int(record.get("repo_id")),
            str(record.get("repo_name") or ""),
            created_at_value,
            str(record.get("payload_json") or ""),
            _as_int(record.get("repo_stargazers_count")),
            str(record.get("repo_primary_language") or ""),
            repo_topics,
            str(record.get("repo_description") or ""),
            str(record.get("repo_full_metadata_json") or ""),
            str(record.get("repo_readme_text") or ""),
            str(record.get("repo_issues_json") or ""),
        )

    @staticmethod
    def _optional_date(value: date | None) -> str | None:
        return value.isoformat() if value is not None else None

    def _current_row_count(self, client: Client) -> int:
        try:
            rows = client.execute(_COUNT_ROWS_QUERY)
        except ClickHouseError as exc:
            raise ClickHouseBackfillError(
                f"Failed to inspect github_data row count: {exc}"
            ) from exc
        if not rows or rows[0][0] is None:
            return 0
        return int(rows[0][0])

    def _truncate_existing_rows(self, client: Client) -> None:
        try:
            client.execute(_TRUNCATE_TABLE_QUERY)
        except ClickHouseError as exc:
            raise ClickHouseBackfillError(
                f"Failed to truncate github_data before backfill: {exc}"
            ) from exc

    def backfill(
        self,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        force: bool = False,
    ) -> ClickHouseBackfillResult:
        """Insert Parquet archive rows into ClickHouse."""
        if start_date is not None and end_date is not None and start_date > end_date:
            raise ClickHouseBackfillError("start_date must be <= end_date")

        self._ensure_parquet_exists()
        client = self._get_client()
        existing_rows = self._current_row_count(client)
        if existing_rows > 0 and not force:
            raise ClickHouseBackfillError(
                "github_data already contains rows; rerun with force=True to truncate first"
            )
        if existing_rows > 0 and force:
            logger.warning(
                "clickhouse_backfill.truncate_existing_rows",
                existing_rows=existing_rows,
            )
            self._truncate_existing_rows(client)

        parquet_files = self._partition_files(start_date=start_date, end_date=end_date)
        if not parquet_files:
            raise ClickHouseBackfillError("No parquet partitions matched the requested date range")

        inserted_rows = 0
        batch_count = 0
        try:
            for parquet_file in parquet_files:
                parquet_reader = pq.ParquetFile(str(parquet_file))
                for batch in parquet_reader.iter_batches(batch_size=self._batch_size):
                    normalized_rows = [
                        self._normalize_record(record) for record in batch.to_pylist()
                    ]
                    try:
                        client.execute(_INSERT_EVENTS_QUERY, normalized_rows)
                    except ClickHouseError as exc:
                        raise ClickHouseBackfillError(
                            f"Failed to insert parquet batch into github_data: {exc}"
                        ) from exc

                    inserted_rows += len(normalized_rows)
                    batch_count += 1
                    logger.info(
                        "clickhouse_backfill.batch_written",
                        batch_count=batch_count,
                        inserted_rows=inserted_rows,
                        parquet_file=str(parquet_file),
                    )
        except (OSError, pa.ArrowInvalid) as exc:
            raise ClickHouseBackfillError(
                f"Failed to scan parquet archive for ClickHouse backfill: {exc}"
            ) from exc

        logger.info(
            "clickhouse_backfill.completed",
            inserted_rows=inserted_rows,
            batch_count=batch_count,
            start_date=self._optional_date(start_date),
            end_date=self._optional_date(end_date),
        )
        return ClickHouseBackfillResult(
            inserted_rows=inserted_rows,
            batch_count=batch_count,
            start_date=start_date,
            end_date=end_date,
        )
