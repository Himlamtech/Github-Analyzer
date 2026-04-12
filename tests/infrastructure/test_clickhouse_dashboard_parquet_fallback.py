"""Regression tests for ClickHouseDashboardService Parquet fallback behavior."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

import pyarrow as pa
import pyarrow.parquet as pq

from university.github.src.domain.exceptions import DashboardQueryError
from university.github.src.infrastructure.storage.clickhouse_dashboard_service import (
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


def _write_repo_event(
    path: Path,
    *,
    repo_id: int,
    repo_name: str,
    created_at: str,
    stargazers_count: int,
    primary_language: str,
    topics: list[str],
    description: str,
    event_type: str = "WatchEvent",
) -> None:
    _write_parquet(
        path,
        {
            "event_id": [f"evt-{repo_id}-{event_type.lower()}"],
            "actor_id": [repo_id],
            "actor_login": [f"user-{repo_id}"],
            "repo_id": [repo_id],
            "repo_name": [repo_name],
            "created_at": [created_at],
            "payload_json": ["{}"],
            "repo_stargazers_count": [stargazers_count],
            "repo_primary_language": [primary_language],
            "repo_topics": [topics],
            "repo_description": [description],
            "repo_full_metadata_json": [
                (
                    '{"full_name":"%s","html_url":"https://github.com/%s",'
                    '"description":"%s","language":"%s","topics":%s,'
                    '"stargazers_count":%d,"watchers_count":%d,'
                    '"owner":{"login":"%s","avatar_url":"https://avatars.githubusercontent.com/u/%d"},'
                    '"license":{"name":"MIT"}}'
                )
                % (
                    repo_name,
                    repo_name,
                    description,
                    primary_language,
                    str(topics).replace("'", '"'),
                    stargazers_count,
                    stargazers_count,
                    repo_name.split("/")[0],
                    repo_id,
                )
            ],
            "repo_readme_text": [description],
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


async def test_get_category_summary_parquet_fallback_derives_ai_categories(
    tmp_path: Path,
) -> None:
    day_dir = tmp_path / "event_date=2026-03-30"
    _write_repo_event(
        day_dir / "event_type=WatchEvent" / "agent.parquet",
        repo_id=201,
        repo_name="browser-use/browser-use",
        created_at="2026-03-30T12:00:00+00:00",
        stargazers_count=50_000,
        primary_language="Python",
        topics=["browser-use", "agent", "automation"],
        description="Browser agents for automation.",
    )
    _write_repo_event(
        day_dir / "event_type=WatchEvent" / "llm.parquet",
        repo_id=202,
        repo_name="openai/gpt-5",
        created_at="2026-03-30T12:10:00+00:00",
        stargazers_count=80_000,
        primary_language="Python",
        topics=["llm", "transformer"],
        description="Foundation language model stack.",
    )
    _write_repo_event(
        day_dir / "event_type=WatchEvent" / "other.parquet",
        repo_id=203,
        repo_name="public-apis/public-apis",
        created_at="2026-03-30T12:20:00+00:00",
        stargazers_count=400_000,
        primary_language="Python",
        topics=["apis"],
        description="A collective list of free APIs.",
    )

    service = _make_service(str(tmp_path))

    with patch.object(service, "_execute_query", side_effect=DashboardQueryError("down")):
        result = await service.get_category_summary(days=1000, limit=10)

    categories = {item["category"] for item in result}
    assert "Agent" in categories
    assert "LLM" in categories
    assert "Other" not in categories


async def test_get_language_breakdown_parquet_fallback_returns_star_count_shape(
    tmp_path: Path,
) -> None:
    day_dir = tmp_path / "event_date=2026-03-30"
    _write_repo_event(
        day_dir / "event_type=WatchEvent" / "agent.parquet",
        repo_id=301,
        repo_name="browser-use/browser-use",
        created_at="2026-03-30T12:00:00+00:00",
        stargazers_count=50_000,
        primary_language="Python",
        topics=["browser-use", "agent"],
        description="Browser agents for automation.",
    )
    _write_repo_event(
        day_dir / "event_type=WatchEvent" / "multimodal.parquet",
        repo_id=302,
        repo_name="openai/voice-lab",
        created_at="2026-03-30T12:05:00+00:00",
        stargazers_count=25_000,
        primary_language="TypeScript",
        topics=["audio", "speech", "multimodal"],
        description="Speech and audio generation stack.",
    )

    service = _make_service(str(tmp_path))

    with patch.object(service, "_execute_query", side_effect=DashboardQueryError("down")):
        result = await service.get_language_breakdown(days=1000, limit=10)

    assert {item["language"] for item in result} == {"Python", "TypeScript"}
    assert all("star_count" in item for item in result)
