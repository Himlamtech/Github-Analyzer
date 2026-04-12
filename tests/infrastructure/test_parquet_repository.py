"""Unit tests for ParquetEventRepository — uses a real temp directory."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

import pyarrow.parquet as pq
import pytest

from src.infrastructure.storage.parquet_repository import ParquetEventRepository

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def repo(tmp_path: Path) -> ParquetEventRepository:
    """Return a ParquetEventRepository backed by a temporary directory."""
    return ParquetEventRepository(base_path=str(tmp_path))


@pytest.fixture
def sample_records() -> list[dict[str, object]]:
    """Minimal valid records that satisfy the Parquet schema."""
    return [
        {
            "event_id": "evt_001",
            "event_type": "WatchEvent",
            "actor_id": 1001,
            "actor_login": "user_a",
            "repo_id": 5001,
            "repo_name": "openai/gpt-5",
            "created_at": "2024-06-15T12:00:00+00:00",
            "payload_json": "{}",
            "public": True,
        },
        {
            "event_id": "evt_002",
            "event_type": "WatchEvent",
            "actor_id": 1002,
            "actor_login": "user_b",
            "repo_id": 5001,
            "repo_name": "openai/gpt-5",
            "created_at": "2024-06-15T13:00:00+00:00",
            "payload_json": "{}",
            "public": True,
        },
    ]


class TestParquetRepositoryAppend:
    """Tests for write operations."""

    async def test_append_batch_writes_correct_row_count(
        self,
        repo: ParquetEventRepository,
        sample_records: list[dict[str, object]],
    ) -> None:
        """Happy path: append_batch returns number of records written."""
        written = await repo.append_batch(
            records=sample_records,
            event_date=date(2024, 6, 15),
            event_type="WatchEvent",
        )
        assert written == len(sample_records)

    async def test_append_batch_creates_parquet_file(
        self,
        repo: ParquetEventRepository,
        sample_records: list[dict[str, object]],
        tmp_path: Path,
    ) -> None:
        """A Parquet file must exist after append_batch."""
        event_date = date(2024, 6, 15)
        await repo.append_batch(
            records=sample_records,
            event_date=event_date,
            event_type="WatchEvent",
        )
        partition_dir = tmp_path / "event_date=2024-06-15" / "event_type=WatchEvent"
        parquet_files = list(partition_dir.glob("*.parquet"))
        assert len(parquet_files) == 1

    async def test_append_empty_batch_returns_zero(self, repo: ParquetEventRepository) -> None:
        """Edge case: empty records list must return 0 without creating files."""
        result = await repo.append_batch(
            records=[], event_date=date(2024, 6, 15), event_type="WatchEvent"
        )
        assert result == 0

    async def test_parquet_file_is_readable_after_write(
        self,
        repo: ParquetEventRepository,
        sample_records: list[dict[str, object]],
        tmp_path: Path,
    ) -> None:
        """Written Parquet file must be readable with correct row count."""
        event_date = date(2024, 6, 15)
        await repo.append_batch(
            records=sample_records,
            event_date=event_date,
            event_type="WatchEvent",
        )
        partition_dir = tmp_path / "event_date=2024-06-15" / "event_type=WatchEvent"
        file_path = next(iter(partition_dir.glob("*.parquet")))
        table = pq.ParquetFile(str(file_path)).read()
        assert table.num_rows == len(sample_records)


class TestParquetRepositoryRead:
    """Tests for read operations."""

    async def test_read_partition_returns_written_records(
        self,
        repo: ParquetEventRepository,
        sample_records: list[dict[str, object]],
    ) -> None:
        """read_partition must return the same records that were written."""
        event_date = date(2024, 6, 15)
        await repo.append_batch(
            records=sample_records,
            event_date=event_date,
            event_type="WatchEvent",
        )
        results = await repo.read_partition(event_date=event_date, event_type="WatchEvent")
        assert len(results) == len(sample_records)

    async def test_read_nonexistent_partition_returns_empty_list(
        self, repo: ParquetEventRepository
    ) -> None:
        """Edge case: reading a partition that doesn't exist returns []."""
        results = await repo.read_partition(event_date=date(2020, 1, 1), event_type="WatchEvent")
        assert results == []

    async def test_read_all_event_types_returns_combined_records(
        self,
        repo: ParquetEventRepository,
        sample_records: list[dict[str, object]],
    ) -> None:
        """read_partition without event_type must return records from all types."""
        event_date = date(2024, 6, 15)
        fork_records = [
            {**r, "event_id": f"fork_{r['event_id']}", "event_type": "ForkEvent"}
            for r in sample_records
        ]
        await repo.append_batch(
            records=sample_records, event_date=event_date, event_type="WatchEvent"
        )
        await repo.append_batch(
            records=fork_records, event_date=event_date, event_type="ForkEvent"
        )
        all_records = await repo.read_partition(event_date=event_date)
        assert len(all_records) == len(sample_records) + len(fork_records)
