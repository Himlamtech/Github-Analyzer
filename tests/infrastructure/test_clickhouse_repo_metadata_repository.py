"""Unit tests for ClickHouseRepoMetadataRepository history writes."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from src.domain.value_objects.repo_category import RepoCategory
from src.domain.value_objects.repo_metadata import RepoLicense, RepoMetadata, RepoOwner
from src.infrastructure.storage.clickhouse_repo_metadata_repository import (
    ClickHouseRepoMetadataRepository,
)


def _repo_metadata() -> RepoMetadata:
    now = datetime(2024, 6, 15, 12, 0, tzinfo=UTC)
    return RepoMetadata(
        repo_id=1,
        repo_full_name="torvalds/linux",
        repo_name="linux",
        node_id="node-1",
        private=False,
        html_url="https://github.com/torvalds/linux",
        clone_url="https://github.com/torvalds/linux.git",
        homepage="",
        stargazers_count=150000,
        watchers_count=150000,
        forks_count=50000,
        open_issues_count=1000,
        network_count=50000,
        subscribers_count=7000,
        size_kb=1024,
        github_created_at=now,
        github_updated_at=now,
        github_pushed_at=now,
        primary_language="C",
        topics=("kernel", "operating-system"),
        visibility="public",
        default_branch="master",
        description="Linux kernel source tree",
        category=RepoCategory.OTHER,
        is_fork=False,
        is_archived=False,
        is_disabled=False,
        has_issues=False,
        has_wiki=False,
        has_discussions=False,
        has_pages=False,
        allow_forking=True,
        is_template=False,
        owner=RepoOwner(
            login="torvalds",
            owner_id=1024025,
            owner_type="User",
            avatar_url="https://avatars.githubusercontent.com/u/1024025",
        ),
        license=RepoLicense(
            key="other",
            name="Other",
            spdx_id="NOASSERTION",
        ),
        rank=1,
        fetched_at=now,
        refreshed_at=now,
    )


async def test_append_history_batch_creates_table_and_inserts_rows() -> None:
    repo = _repo_metadata()
    client = MagicMock()
    repository = ClickHouseRepoMetadataRepository(
        host="localhost",
        port=9000,
        user="default",
        password="secret",
        database="github_analyzer",
    )

    with patch.object(repository, "_get_client", return_value=client):
        await repository.append_history_batch([repo], snapshot_source="sync_repo_metadata")

    assert client.execute.call_count == 2
    create_query = str(client.execute.call_args_list[0].args[0])
    insert_query = str(client.execute.call_args_list[1].args[0])
    insert_rows = client.execute.call_args_list[1].args[1]

    assert "CREATE TABLE IF NOT EXISTS repo_metadata_history" in create_query
    assert "INSERT INTO repo_metadata_history" in insert_query
    assert insert_rows[0][-2] == "sync_repo_metadata"
    assert "torvalds/linux" in insert_rows[0][-1]
