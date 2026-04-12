"""Parquet-backed implementation of RawEventRepositoryABC.

Uses PyArrow directly (not Spark) for lightweight writes from the producer
service.  Spark is responsible for the streaming pipeline writes; this class
handles programmatic batch append operations from tests and utilities.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING, cast

import pyarrow as pa  # type: ignore[import-untyped]
import pyarrow.parquet as pq  # type: ignore[import-untyped]
import structlog

from src.domain.exceptions import ParquetWriteError
from src.domain.repositories.raw_event_repository import RawEventRepositoryABC

if TYPE_CHECKING:
    from datetime import date

logger = structlog.get_logger(__name__)

# PyArrow schema for Parquet files — aligns with PARQUET_EVENT_SCHEMA in schemas.py
_PARQUET_SCHEMA = pa.schema(
    [
        pa.field("event_id", pa.string(), nullable=False),
        pa.field("event_type", pa.string(), nullable=False),
        pa.field("actor_id", pa.int64(), nullable=False),
        pa.field("actor_login", pa.string(), nullable=False),
        pa.field("repo_id", pa.int64(), nullable=False),
        pa.field("repo_name", pa.string(), nullable=False),
        pa.field("created_at", pa.string(), nullable=False),
        pa.field("payload_json", pa.string(), nullable=True),
        pa.field("public", pa.bool_(), nullable=True),
    ]
)


class ParquetEventRepository(RawEventRepositoryABC):
    """Appends and reads raw event records from partitioned Parquet files.

    Partition layout:
        ``{base_path}/event_date=YYYY-MM-DD/event_type=WatchEvent/*.parquet``

    Args:
        base_path: Root directory for the Parquet archive.
    """

    def __init__(self, base_path: str) -> None:
        self._base_path = Path(base_path)

    def _partition_path(self, event_date: date, event_type: str) -> Path:
        """Compute the Hive-style partition directory path.

        Args:
            event_date:  Date partition key.
            event_type:  Event type partition key.

        Returns:
            Absolute Path to the partition directory.
        """
        return self._base_path / f"event_date={event_date}" / f"event_type={event_type}"

    async def append_batch(
        self,
        records: list[dict[str, object]],
        event_date: date,
        event_type: str,
    ) -> int:
        """Append records to the appropriate Parquet partition.

        Files are written with Snappy compression.  The filename uses the
        microsecond-level timestamp to avoid collisions under concurrent writers.

        Args:
            records:    List of serialisable event dictionaries.
            event_date: Hive partition key — determines the date folder.
            event_type: Hive partition key — determines the event_type folder.

        Returns:
            Number of records written.

        Raises:
            ParquetWriteError: If the write operation fails.
        """
        if not records:
            return 0

        return await asyncio.to_thread(self._write_parquet_sync, records, event_date, event_type)

    def _write_parquet_sync(
        self,
        records: list[dict[str, object]],
        event_date: date,
        event_type: str,
    ) -> int:
        """Synchronous Parquet write (runs in thread executor).

        Args:
            records:    Records to write.
            event_date: Partition date.
            event_type: Partition event type.

        Returns:
            Number of records written.
        """
        import time as _time

        partition_dir = self._partition_path(event_date, event_type)
        partition_dir.mkdir(parents=True, exist_ok=True)

        file_path = partition_dir / f"part_{int(_time.time() * 1_000_000)}.parquet"

        try:
            table = pa.Table.from_pylist(records, schema=_PARQUET_SCHEMA)
            pq.write_table(table, str(file_path), compression="snappy")
            logger.debug(
                "parquet_repository.batch_written",
                path=str(file_path),
                rows=len(records),
            )
            return len(records)
        except (pa.ArrowInvalid, OSError) as exc:
            raise ParquetWriteError(
                f"Failed to write Parquet batch to {file_path}: {exc}"
            ) from exc

    async def read_partition(
        self,
        event_date: date,
        event_type: str | None = None,
    ) -> list[dict[str, object]]:
        """Read all records from the specified partition.

        Args:
            event_date:  Date partition to read.
            event_type:  If provided, read only this event type sub-partition.

        Returns:
            List of raw event dictionaries.
        """
        return await asyncio.to_thread(self._read_parquet_sync, event_date, event_type)

    def _read_parquet_sync(
        self,
        event_date: date,
        event_type: str | None,
    ) -> list[dict[str, object]]:
        """Synchronous Parquet read (runs in thread executor).

        Args:
            event_date: Partition date.
            event_type: Optional event type filter.

        Returns:
            List of event dicts.
        """
        if event_type is not None:
            search_dir = self._partition_path(event_date, event_type)
            pattern = "*.parquet"
        else:
            search_dir = self._base_path / f"event_date={event_date}"
            pattern = "**/*.parquet"

        if not search_dir.exists():
            return []

        files = list(search_dir.glob(pattern))
        if not files:
            return []

        try:
            # Read each physical file directly to avoid PyArrow inferring Hive
            # partitions from parent paths like ``event_type=WatchEvent``.
            tables = [pq.ParquetFile(str(file_path)).read() for file_path in files]
            combined = pa.concat_tables(tables)
            return cast("list[dict[str, object]]", combined.to_pylist())
        except (pa.ArrowInvalid, OSError) as exc:
            logger.error(
                "parquet_repository.read_failed",
                path=str(search_dir),
                error=str(exc),
            )
            return []
