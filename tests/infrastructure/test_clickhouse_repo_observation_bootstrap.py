"""Unit tests for ClickHouseRepoObservationBootstrapService."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from university.github.src.infrastructure.storage.clickhouse_repo_observation_bootstrap import (
    ClickHouseRepoObservationBootstrapService,
)


async def test_execute_creates_schema_and_backfills_when_targets_are_empty() -> None:
    client = MagicMock()
    client.execute.side_effect = [
        [],
        [],
        [(5,)],
        [(0,)],
        [],
        [(0,)],
        [],
    ]
    service = ClickHouseRepoObservationBootstrapService(
        host="localhost",
        port=9000,
        user="default",
        password="secret",
        database="github_analyzer",
    )

    with patch.object(service, "_get_client", return_value=client):
        await service.execute()

    queries = [str(call.args[0]) for call in client.execute.call_args_list]
    assert "CREATE TABLE IF NOT EXISTS repo_metadata_history" in queries[0]
    assert (
        "CREATE MATERIALIZED VIEW IF NOT EXISTS github_data_to_repo_metadata_history_mv"
        in queries[1]
    )
    assert queries[2] == "SELECT count() FROM github_data"
    assert queries[3] == "SELECT count() FROM repo_metadata"
    assert "INSERT INTO repo_metadata" in queries[4]
    assert queries[5] == "SELECT count() FROM repo_metadata_history"
    assert "INSERT INTO repo_metadata_history" in queries[6]


async def test_execute_skips_backfill_when_github_data_is_empty() -> None:
    client = MagicMock()
    client.execute.side_effect = [
        [],
        [],
        [(0,)],
    ]
    service = ClickHouseRepoObservationBootstrapService(
        host="localhost",
        port=9000,
        user="default",
        password="secret",
        database="github_analyzer",
    )

    with patch.object(service, "_get_client", return_value=client):
        await service.execute()

    queries = [str(call.args[0]) for call in client.execute.call_args_list]
    assert len(queries) == 3
    assert queries[2] == "SELECT count() FROM github_data"
