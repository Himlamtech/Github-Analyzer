"""ClickHouse-backed implementation of RepoMetadataRepositoryABC.

Uses ``clickhouse-driver`` (sync) wrapped in ``asyncio.to_thread`` for
non-blocking operation in the async application layer.

Table targeted: ``repo_metadata`` — ReplacingMergeTree(refreshed_at).
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, cast

from clickhouse_driver import Client
from clickhouse_driver.errors import Error as ClickHouseError
from clickhouse_driver.errors import NetworkError as ClickHouseNetworkError
import structlog

from src.domain.exceptions import (
    ClickHouseConnectionError,
    ClickHouseWriteError,
    DashboardQueryError,
)
from src.domain.repositories.repo_metadata_repository import RepoMetadataRepositoryABC

logger = structlog.get_logger(__name__)

if TYPE_CHECKING:
    from src.domain.value_objects.repo_category import RepoCategory
    from src.domain.value_objects.repo_metadata import RepoMetadata

_INSERT_BATCH_SIZE = 1_000

_INSERT_QUERY = """
INSERT INTO repo_metadata (
    repo_id, repo_full_name, repo_name, node_id, private,
    html_url, clone_url, homepage,
    stargazers_count, watchers_count, forks_count, open_issues_count,
    network_count, subscribers_count, size_kb,
    github_created_at, github_updated_at, github_pushed_at,
    primary_language, topics, visibility, default_branch, description, category,
    is_fork, is_archived, is_disabled, has_issues, has_wiki,
    has_discussions, has_pages, allow_forking, is_template,
    owner_login, owner_id, owner_type, owner_avatar_url,
    license_key, license_name, license_spdx_id,
    rank, fetched_at, refreshed_at
) VALUES
"""

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

_HISTORY_INSERT_QUERY = """
INSERT INTO repo_metadata_history (
    repo_id, repo_full_name, repo_name, node_id, private,
    html_url, clone_url, homepage,
    stargazers_count, watchers_count, forks_count, open_issues_count,
    network_count, subscribers_count, size_kb,
    github_created_at, github_updated_at, github_pushed_at,
    primary_language, topics, visibility, default_branch, description, category,
    is_fork, is_archived, is_disabled, has_issues, has_wiki,
    has_discussions, has_pages, allow_forking, is_template,
    owner_login, owner_id, owner_type, owner_avatar_url,
    license_key, license_name, license_spdx_id,
    rank, fetched_at, refreshed_at, snapshot_at, snapshot_source, snapshot_key
) VALUES
"""

_TOP_BY_CATEGORY_QUERY = """
SELECT
    rm.repo_id, rm.repo_full_name, rm.repo_name, rm.node_id, rm.private,
    rm.html_url, rm.clone_url, rm.homepage,
    rm.stargazers_count, rm.watchers_count, rm.forks_count, rm.open_issues_count,
    rm.network_count, rm.subscribers_count, rm.size_kb,
    rm.github_created_at, rm.github_updated_at, rm.github_pushed_at,
    rm.primary_language, rm.topics, rm.visibility, rm.default_branch,
    rm.description, rm.category,
    rm.is_fork, rm.is_archived, rm.is_disabled, rm.has_issues, rm.has_wiki,
    rm.has_discussions, rm.has_pages, rm.allow_forking, rm.is_template,
    rm.owner_login, rm.owner_id, rm.owner_type, rm.owner_avatar_url,
    rm.license_key, rm.license_name, rm.license_spdx_id,
    rm.rank, rm.fetched_at, rm.refreshed_at,
    COALESCE(rsc.star_count_sum, 0) AS star_count_in_window
FROM repo_metadata AS rm
FINAL
LEFT JOIN (
    SELECT repo_name, SUM(star_count) AS star_count_sum
    FROM repo_star_counts
    WHERE event_date >= today() - INTERVAL %(days)s DAY
    GROUP BY repo_name
) AS rsc ON rsc.repo_name = rm.repo_full_name
WHERE rm.category = %(category)s
ORDER BY star_count_in_window DESC
LIMIT %(limit)s
"""

_TRENDING_QUERY = """
SELECT
    rm.repo_id, rm.repo_full_name, rm.repo_name, rm.node_id, rm.private,
    rm.html_url, rm.clone_url, rm.homepage,
    rm.stargazers_count, rm.watchers_count, rm.forks_count, rm.open_issues_count,
    rm.network_count, rm.subscribers_count, rm.size_kb,
    rm.github_created_at, rm.github_updated_at, rm.github_pushed_at,
    rm.primary_language, rm.topics, rm.visibility, rm.default_branch,
    rm.description, rm.category,
    rm.is_fork, rm.is_archived, rm.is_disabled, rm.has_issues, rm.has_wiki,
    rm.has_discussions, rm.has_pages, rm.allow_forking, rm.is_template,
    rm.owner_login, rm.owner_id, rm.owner_type, rm.owner_avatar_url,
    rm.license_key, rm.license_name, rm.license_spdx_id,
    rm.rank, rm.fetched_at, rm.refreshed_at,
    COALESCE(rsc.star_count_sum, 0) AS star_count_in_window
FROM repo_metadata AS rm
FINAL
LEFT JOIN (
    SELECT repo_name, SUM(star_count) AS star_count_sum
    FROM repo_star_counts
    WHERE event_date >= today() - INTERVAL %(days)s DAY
    GROUP BY repo_name
) AS rsc ON rsc.repo_name = rm.repo_full_name
ORDER BY star_count_in_window DESC
LIMIT %(limit)s
"""

_CATEGORY_SUMMARY_QUERY = """
SELECT
    rm.category,
    count() AS repo_count,
    SUM(rm.stargazers_count) AS total_stars,
    argMax(rm.repo_full_name, rm.stargazers_count) AS top_repo_name,
    MAX(rm.stargazers_count) AS top_repo_stars,
    COALESCE(SUM(rsc.star_count_sum), 0) AS weekly_star_delta
FROM repo_metadata AS rm
FINAL
LEFT JOIN (
    SELECT repo_name, SUM(star_count) AS star_count_sum
    FROM repo_star_counts
    WHERE event_date >= today() - INTERVAL 7 DAY
    GROUP BY repo_name
) AS rsc ON rsc.repo_name = rm.repo_full_name
GROUP BY rm.category
ORDER BY total_stars DESC
"""


class ClickHouseRepoMetadataRepository(RepoMetadataRepositoryABC):
    """Persists RepoMetadata value objects to the ClickHouse repo_metadata table.

    Args:
        host:     ClickHouse server hostname.
        port:     Native TCP protocol port (default: 9000).
        user:     ClickHouse username.
        password: ClickHouse password.
        database: Target database name.
    """

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
        """Create a new ClickHouse client connection.

        Returns:
            A connected ClickHouse Client.

        Raises:
            ClickHouseConnectionError: If the connection cannot be established.
        """
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

    def _execute_bulk_insert(
        self,
        client: Client,
        query: str,
        rows: list[tuple[Any, ...]],
    ) -> None:
        """Execute a bulk INSERT with retry on network errors.

        Args:
            client: Active ClickHouse client.
            query:  INSERT INTO ... VALUES query string.
            rows:   List of row tuples.

        Raises:
            ClickHouseWriteError: If the insert fails after 3 attempts.
        """
        import time

        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                client.execute(query, rows)
                return
            except ClickHouseNetworkError as exc:
                if attempt == max_attempts:
                    raise ClickHouseWriteError(
                        f"ClickHouse bulk insert failed after {max_attempts} attempts: {exc}"
                    ) from exc
                backoff = 2 ** (attempt - 1)
                logger.warning(
                    "clickhouse_repo_metadata.retry",
                    attempt=attempt,
                    backoff=backoff,
                    error=str(exc),
                )
                time.sleep(backoff)
            except ClickHouseError as exc:
                raise ClickHouseWriteError(f"ClickHouse insert error: {exc}") from exc

    def _repo_to_row(self, repo: RepoMetadata) -> tuple[Any, ...]:
        """Convert a RepoMetadata value object to an INSERT row tuple.

        Column order must match _INSERT_QUERY exactly.
        """
        return (
            repo.repo_id,
            repo.repo_full_name,
            repo.repo_name,
            repo.node_id,
            int(repo.private),
            repo.html_url,
            repo.clone_url,
            repo.homepage,
            repo.stargazers_count,
            repo.watchers_count,
            repo.forks_count,
            repo.open_issues_count,
            repo.network_count,
            repo.subscribers_count,
            repo.size_kb,
            repo.github_created_at,
            repo.github_updated_at,
            repo.github_pushed_at,
            repo.primary_language,
            list(repo.topics),
            repo.visibility,
            repo.default_branch,
            repo.description,
            str(repo.category),
            int(repo.is_fork),
            int(repo.is_archived),
            int(repo.is_disabled),
            int(repo.has_issues),
            int(repo.has_wiki),
            int(repo.has_discussions),
            int(repo.has_pages),
            int(repo.allow_forking),
            int(repo.is_template),
            repo.owner.login,
            repo.owner.owner_id,
            repo.owner.owner_type,
            repo.owner.avatar_url,
            repo.license.key,
            repo.license.name,
            repo.license.spdx_id,
            repo.rank,
            repo.fetched_at,
            repo.refreshed_at,
        )

    def _repo_to_history_row(
        self,
        repo: RepoMetadata,
        snapshot_source: str,
    ) -> tuple[Any, ...]:
        """Convert a RepoMetadata value object to a history INSERT row tuple."""
        snapshot_key = (
            f"{snapshot_source}:{repo.repo_full_name}:{repo.refreshed_at.isoformat()}:"
            f"{repo.fetched_at.isoformat()}"
        )
        return (*self._repo_to_row(repo), repo.refreshed_at, snapshot_source, snapshot_key)

    def _ensure_history_table(self, client: Client) -> None:
        """Create the history table when running against an existing database."""
        try:
            client.execute(_CREATE_HISTORY_TABLE_QUERY)
        except ClickHouseError as exc:
            raise ClickHouseWriteError(
                f"Failed to ensure repo_metadata_history exists: {exc}"
            ) from exc

    def _row_to_dict(self, row: tuple[Any, ...]) -> dict[str, Any]:
        """Map a SELECT result row to a dict with repo metadata + window stats."""

        def _ensure_utc(dt: object) -> datetime:
            if isinstance(dt, datetime):
                return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
            return datetime.now(tz=UTC)

        topics_raw = row[19]
        topics: list[str] = list(topics_raw) if topics_raw else []

        return {
            "repo_id": int(row[0]),
            "repo_full_name": str(row[1]),
            "repo_name": str(row[2]),
            "node_id": str(row[3]),
            "private": bool(row[4]),
            "html_url": str(row[5]),
            "clone_url": str(row[6]),
            "homepage": str(row[7]),
            "stargazers_count": int(row[8]),
            "watchers_count": int(row[9]),
            "forks_count": int(row[10]),
            "open_issues_count": int(row[11]),
            "network_count": int(row[12]),
            "subscribers_count": int(row[13]),
            "size_kb": int(row[14]),
            "github_created_at": _ensure_utc(row[15]),
            "github_updated_at": _ensure_utc(row[16]),
            "github_pushed_at": _ensure_utc(row[17]),
            "primary_language": str(row[18]),
            "topics": topics,
            "visibility": str(row[20]),
            "default_branch": str(row[21]),
            "description": str(row[22]),
            "category": str(row[23]),
            "is_fork": bool(row[24]),
            "is_archived": bool(row[25]),
            "is_disabled": bool(row[26]),
            "has_issues": bool(row[27]),
            "has_wiki": bool(row[28]),
            "has_discussions": bool(row[29]),
            "has_pages": bool(row[30]),
            "allow_forking": bool(row[31]),
            "is_template": bool(row[32]),
            "owner_login": str(row[33]),
            "owner_id": int(row[34]),
            "owner_type": str(row[35]),
            "owner_avatar_url": str(row[36]),
            "license_key": str(row[37]),
            "license_name": str(row[38]),
            "license_spdx_id": str(row[39]),
            "rank": int(row[40]),
            "fetched_at": _ensure_utc(row[41]),
            "refreshed_at": _ensure_utc(row[42]),
            "star_count_in_window": int(row[43]),
        }

    async def upsert_batch(self, repos: list[RepoMetadata]) -> None:
        """Insert or replace a batch of RepoMetadata records.

        Args:
            repos: List of RepoMetadata value objects to upsert.

        Raises:
            ClickHouseWriteError: If the INSERT fails.
        """
        if not repos:
            return

        rows = [self._repo_to_row(r) for r in repos]

        def _write() -> None:
            client = self._get_client()
            for i in range(0, len(rows), _INSERT_BATCH_SIZE):
                chunk = rows[i : i + _INSERT_BATCH_SIZE]
                self._execute_bulk_insert(client, _INSERT_QUERY, chunk)
                logger.debug(
                    "clickhouse_repo_metadata.batch_written",
                    rows=len(chunk),
                    offset=i,
                )

        await asyncio.to_thread(_write)

    async def append_history_batch(
        self,
        repos: list[RepoMetadata],
        snapshot_source: str,
    ) -> None:
        """Append one history snapshot row per repository record."""
        if not repos:
            return

        rows = [self._repo_to_history_row(repo, snapshot_source) for repo in repos]

        def _write() -> None:
            client = self._get_client()
            self._ensure_history_table(client)
            for i in range(0, len(rows), _INSERT_BATCH_SIZE):
                chunk = rows[i : i + _INSERT_BATCH_SIZE]
                self._execute_bulk_insert(client, _HISTORY_INSERT_QUERY, chunk)
                logger.debug(
                    "clickhouse_repo_metadata.history_batch_written",
                    rows=len(chunk),
                    offset=i,
                    snapshot_source=snapshot_source,
                )

        await asyncio.to_thread(_write)

    async def get_top_by_category(
        self,
        category: RepoCategory,
        days: int,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Return top repos in a category ranked by recent star velocity.

        Args:
            category: Filter to this category.
            days:     Look-back window in days.
            limit:    Maximum rows to return.

        Returns:
            List of dicts with repo metadata + star_count_in_window.
        """
        params: dict[str, Any] = {
            "category": str(category),
            "days": days,
            "limit": limit,
        }

        def _query() -> list[tuple[Any, ...]]:
            client = self._get_client()
            try:
                rows = client.execute(_TOP_BY_CATEGORY_QUERY, params)
                return cast("list[tuple[Any, ...]]", rows)
            except ClickHouseError as exc:
                raise DashboardQueryError(f"top_by_category query failed: {exc}") from exc

        rows = await asyncio.to_thread(_query)
        return [self._row_to_dict(row) for row in rows]

    async def get_trending(self, days: int, limit: int) -> list[dict[str, Any]]:
        """Return trending repos by star growth across all categories.

        Args:
            days:  Look-back window in days.
            limit: Maximum rows to return.

        Returns:
            List of dicts with repo metadata + star_count_in_window.
        """
        params: dict[str, Any] = {"days": days, "limit": limit}

        def _query() -> list[tuple[Any, ...]]:
            client = self._get_client()
            try:
                rows = client.execute(_TRENDING_QUERY, params)
                return cast("list[tuple[Any, ...]]", rows)
            except ClickHouseError as exc:
                raise DashboardQueryError(f"trending query failed: {exc}") from exc

        rows = await asyncio.to_thread(_query)
        return [self._row_to_dict(row) for row in rows]

    async def get_category_summary(self) -> list[dict[str, Any]]:
        """Return per-category aggregate stats.

        Returns:
            List of dicts: category, repo_count, total_stars,
            top_repo_name, top_repo_stars, weekly_star_delta.
        """

        def _query() -> list[tuple[Any, ...]]:
            client = self._get_client()
            try:
                rows = client.execute(_CATEGORY_SUMMARY_QUERY)
                return cast("list[tuple[Any, ...]]", rows)
            except ClickHouseError as exc:
                raise DashboardQueryError(f"category_summary query failed: {exc}") from exc

        rows = await asyncio.to_thread(_query)
        return [
            {
                "category": str(row[0]),
                "repo_count": int(row[1]),
                "total_stars": int(row[2]),
                "top_repo_name": str(row[3]),
                "top_repo_stars": int(row[4]),
                "weekly_star_delta": int(row[5]),
            }
            for row in rows
        ]
