"""Regression tests for ClickHouseDashboardService Parquet fallback behavior."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

import pyarrow as pa
import pyarrow.parquet as pq

from src.infrastructure.storage.clickhouse_dashboard_service import (
    ClickHouseDashboardService,
)

if TYPE_CHECKING:
    from pathlib import Path


def _make_service(parquet_base_path: str) -> ClickHouseDashboardService:
    return ClickHouseDashboardService(
        host="localhost",
        port=9000,
        user="default",
        password="",
        database="github_analyzer",
        parquet_base_path=parquet_base_path,
    )


def _write_parquet(path: Path, columns: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.table(columns), path)


def _write_old_watch_schema(path: Path) -> None:
    _write_parquet(
        path,
        {
            "event_id": ["evt_old"],
            "actor_id": [1],
            "actor_login": ["dev_a"],
            "repo_id": [101],
            "repo_name": ["openai/gpt-5"],
            "created_at": ["2024-06-15T12:00:00+00:00"],
            "payload_json": ["{}"],
            "public": [True],
        },
    )


def _write_new_watch_schema(path: Path) -> None:
    _write_parquet(
        path,
        {
            "event_id": ["evt_new"],
            "actor_id": [2],
            "actor_login": ["dev_b"],
            "repo_id": [101],
            "repo_name": ["openai/gpt-5"],
            "created_at": ["2024-06-15T13:00:00+00:00"],
            "payload_json": ["{}"],
            "repo_stargazers_count": [123],
            "repo_primary_language": ["Python"],
            "repo_topics": [["llm", "agent"]],
            "repo_description": ["An AI repository."],
            "repo_full_metadata_json": ['{"full_name":"openai/gpt-5"}'],
            "repo_readme_text": ["README"],
            "repo_issues_json": ["[]"],
            "public": [True],
        },
    )


async def test_get_top_repos_parquet_fallback_handles_mixed_schema_files(
    tmp_path: Path,
) -> None:
    """Fallback query must work when Parquet files have evolved schemas."""
    watch_dir = tmp_path / "event_date=2024-06-15" / "event_type=WatchEvent"
    _write_old_watch_schema(watch_dir / "part-old.parquet")
    _write_new_watch_schema(watch_dir / "part-new.parquet")

    service = _make_service(str(tmp_path))

    with (
        patch.object(service, "_repo_metadata_table_exists", return_value=False),
        patch.object(service, "_execute_query", return_value=[]),
    ):
        result = await service.get_top_repos(category=None, days=1000, limit=10)

    assert len(result) == 1
    assert result[0]["repo_full_name"] == "openai/gpt-5"
    assert result[0]["star_count_in_window"] == 2
    assert result[0]["stargazers_count"] == 123
