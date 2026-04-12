"""Regression tests for AI search candidate fallback from Parquet archives."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

import pyarrow as pa
import pyarrow.parquet as pq

from university.github.src.domain.exceptions import AISearchError
from university.github.src.infrastructure.storage.clickhouse_ai_service import ClickHouseAISearchService

if TYPE_CHECKING:
    from pathlib import Path


def _make_service(parquet_base_path: str) -> ClickHouseAISearchService:
    return ClickHouseAISearchService(
        host="localhost",
        port=9000,
        user="default",
        password="",
        database="github_analyzer",
        parquet_base_path=parquet_base_path,
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
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(
        pa.table(
            {
                "event_id": [f"evt-{repo_id}"],
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
                        '"owner":{"login":"%s","avatar_url":"https://avatars.githubusercontent.com/u/%d"}}'
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
            }
        ),
        path,
    )


async def test_get_candidates_parquet_fallback_filters_by_category_and_language(
    tmp_path: Path,
) -> None:
    day_dir = tmp_path / "event_date=2026-03-30" / "event_type=WatchEvent"
    _write_repo_event(
        day_dir / "agent.parquet",
        repo_id=401,
        repo_name="browser-use/browser-use",
        created_at="2026-03-30T12:00:00+00:00",
        stargazers_count=50_000,
        primary_language="Python",
        topics=["browser-use", "agent", "automation"],
        description="Browser agents for automation.",
    )
    _write_repo_event(
        day_dir / "llm.parquet",
        repo_id=402,
        repo_name="openai/gpt-5",
        created_at="2026-03-30T12:05:00+00:00",
        stargazers_count=80_000,
        primary_language="Python",
        topics=["llm", "transformer"],
        description="Foundation language model stack.",
    )

    service = _make_service(str(tmp_path))

    with patch.object(service, "_execute_query", side_effect=AISearchError("down")):
        result = await service.get_candidates(
            category="Agent",
            primary_language="Python",
            min_stars=1_000,
            days=1000,
            limit=10,
        )

    assert len(result) == 1
    assert result[0].repo.repo_full_name == "browser-use/browser-use"
    assert result[0].repo.category == "Agent"
