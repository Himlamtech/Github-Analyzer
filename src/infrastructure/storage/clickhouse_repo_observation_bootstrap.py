"""Bootstrap ClickHouse repository observation tables from raw GitHub events."""

from __future__ import annotations

import asyncio
from typing import cast

from clickhouse_driver import Client
from clickhouse_driver.errors import Error as ClickHouseError
from clickhouse_driver.errors import NetworkError as ClickHouseNetworkError
import structlog

from university.github.src.domain.exceptions import ClickHouseConnectionError, ClickHouseWriteError

logger = structlog.get_logger(__name__)

_CREATE_HISTORY_TABLE_QUERY = """
CREATE TABLE IF NOT EXISTS repo_metadata_history
(
    repo_id Int64,
    repo_full_name String,
    repo_name String,
    node_id String,
    private UInt8,

    html_url String,
    clone_url String,
    homepage String,

    stargazers_count Int64,
    watchers_count Int64,
    forks_count Int64,
    open_issues_count Int64,
    network_count Int64,
    subscribers_count Int64,
    size_kb Int64,

    github_created_at DateTime('UTC'),
    github_updated_at DateTime('UTC'),
    github_pushed_at DateTime('UTC'),

    primary_language LowCardinality(String),
    topics Array(String),
    visibility LowCardinality(String),
    default_branch String,
    description String,
    category LowCardinality(String),

    is_fork UInt8,
    is_archived UInt8,
    is_disabled UInt8,
    has_issues UInt8,
    has_wiki UInt8,
    has_discussions UInt8,
    has_pages UInt8,
    allow_forking UInt8,
    is_template UInt8,

    owner_login String,
    owner_id Int64,
    owner_type LowCardinality(String),
    owner_avatar_url String,

    license_key String,
    license_name String,
    license_spdx_id String,

    rank Int32,
    fetched_at DateTime('UTC'),
    refreshed_at DateTime('UTC'),
    snapshot_at DateTime('UTC'),
    snapshot_source LowCardinality(String),
    snapshot_key String
)
ENGINE = ReplacingMergeTree(snapshot_at)
PARTITION BY toYYYYMM(snapshot_at)
ORDER BY (repo_full_name, snapshot_source, snapshot_at, snapshot_key)
SETTINGS index_granularity = 8192
"""

_CREATE_HISTORY_MATERIALIZED_VIEW_QUERY = """
CREATE MATERIALIZED VIEW IF NOT EXISTS github_data_to_repo_metadata_history_mv
TO repo_metadata_history
AS
SELECT
    repo_id,
    repo_name AS repo_full_name,
    if(position(repo_name, '/') > 0, splitByChar('/', repo_name)[2], repo_name) AS repo_name,
    '' AS node_id,
    toUInt8(0) AS private,
    concat('https://github.com/', repo_name) AS html_url,
    concat('https://github.com/', repo_name, '.git') AS clone_url,
    '' AS homepage,
    repo_stargazers_count AS stargazers_count,
    repo_stargazers_count AS watchers_count,
    toInt64(0) AS forks_count,
    toInt64(0) AS open_issues_count,
    toInt64(0) AS network_count,
    toInt64(0) AS subscribers_count,
    toInt64(0) AS size_kb,
    created_at AS github_created_at,
    created_at AS github_updated_at,
    created_at AS github_pushed_at,
    repo_primary_language AS primary_language,
    repo_topics AS topics,
    'public' AS visibility,
    'main' AS default_branch,
    repo_description AS description,
    'Other' AS category,
    toUInt8(0) AS is_fork,
    toUInt8(0) AS is_archived,
    toUInt8(0) AS is_disabled,
    toUInt8(1) AS has_issues,
    toUInt8(0) AS has_wiki,
    toUInt8(0) AS has_discussions,
    toUInt8(0) AS has_pages,
    toUInt8(1) AS allow_forking,
    toUInt8(0) AS is_template,
    if(position(repo_name, '/') > 0, splitByChar('/', repo_name)[1], '') AS owner_login,
    toInt64(0) AS owner_id,
    '' AS owner_type,
    '' AS owner_avatar_url,
    '' AS license_key,
    '' AS license_name,
    '' AS license_spdx_id,
    toInt32(0) AS rank,
    created_at AS fetched_at,
    created_at AS refreshed_at,
    created_at AS snapshot_at,
    'github_event' AS snapshot_source,
    event_id AS snapshot_key
FROM github_data
"""

_BACKFILL_REPO_METADATA_QUERY = """
INSERT INTO repo_metadata
SELECT
    repo_id,
    repo_name AS repo_full_name,
    if(position(repo_name, '/') > 0, splitByChar('/', repo_name)[2], repo_name) AS repo_name_only,
    '' AS node_id,
    toUInt8(0) AS private,
    concat('https://github.com/', repo_name) AS html_url,
    concat('https://github.com/', repo_name, '.git') AS clone_url,
    '' AS homepage,
    argMax(repo_stargazers_count, created_at) AS stargazers_count,
    argMax(repo_stargazers_count, created_at) AS watchers_count,
    toInt64(0) AS forks_count,
    toInt64(0) AS open_issues_count,
    toInt64(0) AS network_count,
    toInt64(0) AS subscribers_count,
    toInt64(0) AS size_kb,
    min(created_at) AS github_created_at,
    max(created_at) AS github_updated_at,
    max(created_at) AS github_pushed_at,
    argMax(repo_primary_language, created_at) AS primary_language,
    argMax(repo_topics, created_at) AS topics,
    'public' AS visibility,
    'main' AS default_branch,
    argMax(repo_description, created_at) AS description,
    'Other' AS category,
    toUInt8(0) AS is_fork,
    toUInt8(0) AS is_archived,
    toUInt8(0) AS is_disabled,
    toUInt8(1) AS has_issues,
    toUInt8(0) AS has_wiki,
    toUInt8(0) AS has_discussions,
    toUInt8(0) AS has_pages,
    toUInt8(1) AS allow_forking,
    toUInt8(0) AS is_template,
    if(position(repo_name, '/') > 0, splitByChar('/', repo_name)[1], '') AS owner_login,
    toInt64(0) AS owner_id,
    '' AS owner_type,
    '' AS owner_avatar_url,
    '' AS license_key,
    '' AS license_name,
    '' AS license_spdx_id,
    toInt32(0) AS rank,
    max(created_at) AS fetched_at,
    max(created_at) AS refreshed_at
FROM github_data
GROUP BY repo_id, repo_name
"""

_BACKFILL_HISTORY_QUERY = """
INSERT INTO repo_metadata_history
SELECT
    repo_id,
    repo_name AS repo_full_name,
    if(position(repo_name, '/') > 0, splitByChar('/', repo_name)[2], repo_name) AS repo_name,
    '' AS node_id,
    toUInt8(0) AS private,
    concat('https://github.com/', repo_name) AS html_url,
    concat('https://github.com/', repo_name, '.git') AS clone_url,
    '' AS homepage,
    repo_stargazers_count AS stargazers_count,
    repo_stargazers_count AS watchers_count,
    toInt64(0) AS forks_count,
    toInt64(0) AS open_issues_count,
    toInt64(0) AS network_count,
    toInt64(0) AS subscribers_count,
    toInt64(0) AS size_kb,
    created_at AS github_created_at,
    created_at AS github_updated_at,
    created_at AS github_pushed_at,
    repo_primary_language AS primary_language,
    repo_topics AS topics,
    'public' AS visibility,
    'main' AS default_branch,
    repo_description AS description,
    'Other' AS category,
    toUInt8(0) AS is_fork,
    toUInt8(0) AS is_archived,
    toUInt8(0) AS is_disabled,
    toUInt8(1) AS has_issues,
    toUInt8(0) AS has_wiki,
    toUInt8(0) AS has_discussions,
    toUInt8(0) AS has_pages,
    toUInt8(1) AS allow_forking,
    toUInt8(0) AS is_template,
    if(position(repo_name, '/') > 0, splitByChar('/', repo_name)[1], '') AS owner_login,
    toInt64(0) AS owner_id,
    '' AS owner_type,
    '' AS owner_avatar_url,
    '' AS license_key,
    '' AS license_name,
    '' AS license_spdx_id,
    toInt32(0) AS rank,
    created_at AS fetched_at,
    created_at AS refreshed_at,
    created_at AS snapshot_at,
    'github_event' AS snapshot_source,
    event_id AS snapshot_key
FROM github_data
"""


class ClickHouseRepoObservationBootstrapService:
    """Creates and backfills repository observation storage from `github_data`."""

    def __init__(
        self,
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

    def _count_rows(self, client: Client, table_name: str) -> int:
        rows = client.execute(f"SELECT count() FROM {table_name}")
        if not rows or not rows[0]:
            return 0
        return int(cast("int | str", rows[0][0]))

    def _bootstrap(self) -> None:
        client = self._get_client()
        try:
            client.execute(_CREATE_HISTORY_TABLE_QUERY)
            client.execute(_CREATE_HISTORY_MATERIALIZED_VIEW_QUERY)

            if self._count_rows(client, "github_data") == 0:
                return

            if self._count_rows(client, "repo_metadata") == 0:
                client.execute(_BACKFILL_REPO_METADATA_QUERY)

            if self._count_rows(client, "repo_metadata_history") == 0:
                client.execute(_BACKFILL_HISTORY_QUERY)
        except ClickHouseError as exc:
            raise ClickHouseWriteError(
                f"Failed to bootstrap repo observation tables: {exc}"
            ) from exc

    async def execute(self) -> None:
        """Ensure repo observation history exists and is backfilled."""
        await asyncio.to_thread(self._bootstrap)
        logger.info("clickhouse_repo_observation_bootstrap.complete")
