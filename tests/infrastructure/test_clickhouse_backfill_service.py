from __future__ import annotations

from datetime import UTC, date, datetime
from typing import TYPE_CHECKING

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from src.domain.exceptions import ClickHouseBackfillError
from src.infrastructure.storage.clickhouse_backfill_service import ClickHouseBackfillService

if TYPE_CHECKING:
    from pathlib import Path


class StubClickHouseClient:
    def __init__(self, row_count: int = 0) -> None:
        self.row_count = row_count
        self.inserted_rows: list[tuple[object, ...]] = []
        self.truncated = False

    def execute(
        self,
        query: str,
        params: list[tuple[object, ...]] | None = None,
    ) -> list[tuple[object, ...]]:
        if query.strip().startswith("SELECT count() FROM github_data"):
            return [(self.row_count,)]
        if query.strip().startswith("TRUNCATE TABLE github_data"):
            self.truncated = True
            self.row_count = 0
            return []
        if query.strip().startswith("INSERT INTO github_data"):
            rows = params or []
            self.inserted_rows.extend(rows)
            self.row_count += len(rows)
            return []
        raise AssertionError(query)


def _write_partition(
    tmp_path: Path,
    *,
    event_date: str,
    event_type: str,
    rows: list[dict[str, object]],
) -> None:
    partition_dir = tmp_path / f"event_date={event_date}" / f"event_type={event_type}"
    partition_dir.mkdir(parents=True, exist_ok=True)
    table = pa.table(
        {
            "event_id": [str(row["event_id"]) for row in rows],
            "event_type": [str(row["event_type"]) for row in rows],
            "actor_id": [int(row["actor_id"]) for row in rows],
            "actor_login": [str(row["actor_login"]) for row in rows],
            "repo_id": [int(row["repo_id"]) for row in rows],
            "repo_name": [str(row["repo_name"]) for row in rows],
            "created_at": [row["created_at"] for row in rows],
            "payload_json": [str(row["payload_json"]) for row in rows],
            "repo_stargazers_count": [int(row["repo_stargazers_count"]) for row in rows],
            "repo_primary_language": [str(row["repo_primary_language"]) for row in rows],
            "repo_topics": [row["repo_topics"] for row in rows],
            "repo_description": [str(row["repo_description"]) for row in rows],
            "repo_full_metadata_json": [str(row["repo_full_metadata_json"]) for row in rows],
            "repo_readme_text": [str(row["repo_readme_text"]) for row in rows],
            "repo_issues_json": [str(row["repo_issues_json"]) for row in rows],
        }
    )
    pq.write_table(table, partition_dir / "part-000.parquet")


def _build_service(
    tmp_path: Path,
    stub_client: StubClickHouseClient,
    *,
    batch_size: int = 10_000,
) -> ClickHouseBackfillService:
    service = ClickHouseBackfillService(
        host="localhost",
        port=9000,
        user="github_analyzer",
        password="github_analyzer",
        database="github_analyzer",
        parquet_base_path=str(tmp_path),
        batch_size=batch_size,
    )
    service._get_client = lambda: stub_client  # type: ignore[method-assign]
    return service


def test_backfill_inserts_rows_from_matching_partitions(tmp_path: Path) -> None:
    rows = [
        {
            "event_id": "evt-1",
            "event_type": "WatchEvent",
            "actor_id": 1,
            "actor_login": "alice",
            "repo_id": 101,
            "repo_name": "acme/repo-one",
            "created_at": datetime(2026, 3, 28, 10, 0, tzinfo=UTC),
            "payload_json": "{}",
            "repo_stargazers_count": 11_000,
            "repo_primary_language": "Python",
            "repo_topics": ["ai", "agents"],
            "repo_description": "repo one",
            "repo_full_metadata_json": "{}",
            "repo_readme_text": "readme",
            "repo_issues_json": "[]",
        },
        {
            "event_id": "evt-2",
            "event_type": "ForkEvent",
            "actor_id": 2,
            "actor_login": "bob",
            "repo_id": 102,
            "repo_name": "acme/repo-two",
            "created_at": datetime(2026, 3, 28, 11, 0, tzinfo=UTC),
            "payload_json": "{}",
            "repo_stargazers_count": 12_000,
            "repo_primary_language": "TypeScript",
            "repo_topics": ["web"],
            "repo_description": "repo two",
            "repo_full_metadata_json": "{}",
            "repo_readme_text": "readme",
            "repo_issues_json": "[]",
        },
    ]
    _write_partition(tmp_path, event_date="2026-03-28", event_type="WatchEvent", rows=rows)
    stub_client = StubClickHouseClient()
    service = _build_service(tmp_path, stub_client, batch_size=1)

    result = service.backfill(
        start_date=date(2026, 3, 28),
        end_date=date(2026, 3, 28),
    )

    assert result.inserted_rows == 2
    assert result.batch_count == 2
    assert len(stub_client.inserted_rows) == 2
    assert stub_client.inserted_rows[0][0] == "evt-1"
    assert stub_client.inserted_rows[0][10] == ["ai", "agents"]


def test_backfill_respects_partition_date_window(tmp_path: Path) -> None:
    inside_window_rows = [
        {
            "event_id": "evt-in-window",
            "event_type": "WatchEvent",
            "actor_id": 10,
            "actor_login": "inside",
            "repo_id": 201,
            "repo_name": "acme/repo-window",
            "created_at": datetime(2026, 3, 28, 9, 0, tzinfo=UTC),
            "payload_json": "{}",
            "repo_stargazers_count": 15_000,
            "repo_primary_language": "Python",
            "repo_topics": ["ai"],
            "repo_description": "inside window",
            "repo_full_metadata_json": "{}",
            "repo_readme_text": "readme",
            "repo_issues_json": "[]",
        }
    ]
    outside_window_rows = [
        {
            "event_id": "evt-outside-window",
            "event_type": "WatchEvent",
            "actor_id": 11,
            "actor_login": "outside",
            "repo_id": 202,
            "repo_name": "acme/repo-old",
            "created_at": datetime(2026, 3, 20, 9, 0, tzinfo=UTC),
            "payload_json": "{}",
            "repo_stargazers_count": 9_000,
            "repo_primary_language": "Python",
            "repo_topics": ["legacy"],
            "repo_description": "outside window",
            "repo_full_metadata_json": "{}",
            "repo_readme_text": "readme",
            "repo_issues_json": "[]",
        }
    ]
    _write_partition(
        tmp_path,
        event_date="2026-03-28",
        event_type="WatchEvent",
        rows=inside_window_rows,
    )
    _write_partition(
        tmp_path,
        event_date="2026-03-20",
        event_type="WatchEvent",
        rows=outside_window_rows,
    )
    stub_client = StubClickHouseClient()
    service = _build_service(tmp_path, stub_client)

    result = service.backfill(
        start_date=date(2026, 3, 28),
        end_date=date(2026, 3, 28),
    )

    assert result.inserted_rows == 1
    assert [row[0] for row in stub_client.inserted_rows] == ["evt-in-window"]


def test_backfill_force_truncates_existing_rows_before_insert(tmp_path: Path) -> None:
    rows = [
        {
            "event_id": "evt-1",
            "event_type": "WatchEvent",
            "actor_id": 1,
            "actor_login": "alice",
            "repo_id": 101,
            "repo_name": "acme/repo-one",
            "created_at": datetime(2026, 3, 28, 10, 0, tzinfo=UTC),
            "payload_json": "{}",
            "repo_stargazers_count": 11_000,
            "repo_primary_language": "Python",
            "repo_topics": ["ai"],
            "repo_description": "repo one",
            "repo_full_metadata_json": "{}",
            "repo_readme_text": "readme",
            "repo_issues_json": "[]",
        }
    ]
    _write_partition(tmp_path, event_date="2026-03-28", event_type="WatchEvent", rows=rows)
    stub_client = StubClickHouseClient(row_count=25)
    service = _build_service(tmp_path, stub_client)

    result = service.backfill(force=True)

    assert result.inserted_rows == 1
    assert stub_client.truncated is True
    assert len(stub_client.inserted_rows) == 1


def test_backfill_raises_when_table_not_empty_without_force(tmp_path: Path) -> None:
    rows = [
        {
            "event_id": "evt-1",
            "event_type": "WatchEvent",
            "actor_id": 1,
            "actor_login": "alice",
            "repo_id": 101,
            "repo_name": "acme/repo-one",
            "created_at": datetime(2026, 3, 28, 10, 0, tzinfo=UTC),
            "payload_json": "{}",
            "repo_stargazers_count": 11_000,
            "repo_primary_language": "Python",
            "repo_topics": ["ai"],
            "repo_description": "repo one",
            "repo_full_metadata_json": "{}",
            "repo_readme_text": "readme",
            "repo_issues_json": "[]",
        }
    ]
    _write_partition(tmp_path, event_date="2026-03-28", event_type="WatchEvent", rows=rows)
    stub_client = StubClickHouseClient(row_count=3)
    service = _build_service(tmp_path, stub_client)

    with pytest.raises(ClickHouseBackfillError, match="already contains rows"):
        service.backfill()
