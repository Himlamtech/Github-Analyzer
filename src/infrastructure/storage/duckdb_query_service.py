"""DuckDB-based ad-hoc analytics service over the Parquet archive.

DuckDB runs in-process with read-only access to the Parquet files.
There is no write contention with the Spark streaming job because DuckDB
reads directly from the filesystem without locking Parquet files.

Design: each method opens a fresh in-memory DuckDB connection, runs the
query, and closes it.  This avoids state accumulation and is safe for
concurrent async callers (each ``asyncio.to_thread`` call gets its own
connection).
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import duckdb
import structlog

from src.application.dtos.github_event_dto import HourlyActivityDTO, RepoStarCountDTO
from src.domain.exceptions import DuckDBQueryError

logger = structlog.get_logger(__name__)

if TYPE_CHECKING:
    from datetime import date


class DuckDBQueryService:
    """In-process analytical query service over Parquet files.

    Args:
        base_path: Root directory of the Parquet archive
                   (same as ``PARQUET_BASE_PATH`` setting).
    """

    def __init__(self, base_path: str) -> None:
        self._base_path = base_path.rstrip("/")

    def _connect(self) -> duckdb.DuckDBPyConnection:
        """Open a new read-only DuckDB in-memory connection.

        Returns:
            A fresh DuckDB connection ready for queries.
        """
        return duckdb.connect(database=":memory:", read_only=False)

    async def get_top_repos_by_stars(self, days: int, limit: int = 20) -> list[RepoStarCountDTO]:
        """Return the top repositories by star count over the last N days.

        Reads only WatchEvent partitions for efficiency.

        Args:
            days:  Look-back window in days.
            limit: Maximum number of repos to return.

        Returns:
            List of ``RepoStarCountDTO`` ordered by star count descending.

        Raises:
            DuckDBQueryError: If the query fails.
        """
        glob_path = f"{self._base_path}/event_date=*/event_type=WatchEvent/*.parquet"
        return await asyncio.to_thread(self._run_top_repos_query, glob_path, days, limit)

    def _run_top_repos_query(
        self, glob_path: str, days: int, limit: int
    ) -> list[RepoStarCountDTO]:
        """Synchronous DuckDB query for top repos by stars.

        Args:
            glob_path: Glob pattern to WatchEvent Parquet files.
            days:      Look-back window.
            limit:     Result limit.

        Returns:
            List of RepoStarCountDTO.
        """
        sql = """
        SELECT
            repo_name,
            CAST(event_date AS DATE) AS event_date,
            COUNT(*) AS star_count
        FROM read_parquet(?, hive_partitioning = true, union_by_name = true)
        WHERE CAST(event_date AS DATE) >= CURRENT_DATE - INTERVAL (?) DAY
        GROUP BY repo_name, event_date
        ORDER BY star_count DESC
        LIMIT ?
        """
        try:
            conn = self._connect()
            rows = conn.execute(sql, [glob_path, days, limit]).fetchall()
            conn.close()
            return [
                RepoStarCountDTO(
                    repo_name=str(row[0]),
                    event_date=row[1],
                    star_count=int(row[2]),
                )
                for row in rows
            ]
        except duckdb.Error as exc:
            raise DuckDBQueryError(f"get_top_repos_by_stars failed: {exc}") from exc

    async def get_event_volume_by_type(self, query_date: date) -> dict[str, int]:
        """Return event counts grouped by event type for a specific date.

        Args:
            query_date: UTC date to aggregate.

        Returns:
            Dict mapping event_type string → count.

        Raises:
            DuckDBQueryError: If the query fails.
        """
        date_str = query_date.strftime("%Y-%m-%d")
        glob_path = f"{self._base_path}/event_date={date_str}/event_type=*/*.parquet"
        return await asyncio.to_thread(self._run_volume_query, glob_path)

    def _run_volume_query(self, glob_path: str) -> dict[str, int]:
        """Synchronous DuckDB query for event volume by type.

        Args:
            glob_path: Glob pattern scoped to a single date.

        Returns:
            Dict of event_type → count.
        """
        sql = """
        SELECT
            event_type,
            COUNT(*) AS event_count
        FROM read_parquet(?, hive_partitioning = true, union_by_name = true)
        GROUP BY event_type
        ORDER BY event_count DESC
        """
        try:
            conn = self._connect()
            rows = conn.execute(sql, [glob_path]).fetchall()
            conn.close()
            return {str(row[0]): int(row[1]) for row in rows}
        except duckdb.Error as exc:
            raise DuckDBQueryError(f"get_event_volume_by_type failed: {exc}") from exc

    async def get_hourly_activity(
        self, repo_name: str, query_date: date
    ) -> list[HourlyActivityDTO]:
        """Return per-hour event counts for a specific repo and date.

        Args:
            repo_name:  The ``owner/repo`` repository name.
            query_date: UTC date to analyse.

        Returns:
            List of ``HourlyActivityDTO`` for hours with activity (may be sparse).

        Raises:
            DuckDBQueryError: If the query fails.
        """
        date_str = query_date.strftime("%Y-%m-%d")
        glob_path = f"{self._base_path}/event_date={date_str}/event_type=*/*.parquet"
        return await asyncio.to_thread(self._run_hourly_query, glob_path, repo_name)

    def _run_hourly_query(self, glob_path: str, repo_name: str) -> list[HourlyActivityDTO]:
        """Synchronous DuckDB query for hourly activity.

        Args:
            glob_path: Glob pattern scoped to a single date.
            repo_name: Repository name filter.

        Returns:
            List of HourlyActivityDTO.
        """
        sql = """
        SELECT
            EXTRACT(HOUR FROM CAST(created_at AS TIMESTAMP)) AS hour,
            COUNT(*) AS event_count
        FROM read_parquet(?, hive_partitioning = true, union_by_name = true)
        WHERE repo_name = ?
        GROUP BY hour
        ORDER BY hour ASC
        """
        try:
            conn = self._connect()
            rows = conn.execute(sql, [glob_path, repo_name]).fetchall()
            conn.close()
            return [HourlyActivityDTO(hour=int(row[0]), event_count=int(row[1])) for row in rows]
        except duckdb.Error as exc:
            raise DuckDBQueryError(f"get_hourly_activity failed for {repo_name!r}: {exc}") from exc
