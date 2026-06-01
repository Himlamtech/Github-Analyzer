"""ClickHouseDashboardService — analytical queries powering the dashboard.

Single-responsibility service for the dashboard endpoints.
Uses ``clickhouse-driver`` (sync) wrapped in ``asyncio.to_thread``.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta, timezone
from typing import Any, cast

from clickhouse_driver import Client
from clickhouse_driver.errors import Error as ClickHouseError
from clickhouse_driver.errors import NetworkError as ClickHouseNetworkError
import structlog

from src.domain.exceptions import ClickHouseConnectionError, DashboardQueryError
from src.domain.services.category_classifier import CategoryClassifier
from src.domain.value_objects.repo_category import RepoCategory

logger = structlog.get_logger(__name__)

_GMT7 = timezone(timedelta(hours=7))

_REPO_WINDOW_METRICS_SUBQUERY = """
SELECT
    repo_name,
    countIf(event_type = 'WatchEvent') AS star_count_in_window,
    max(created_at) AS latest_event_at
FROM github_data
WHERE created_at >= now() - INTERVAL %(days)s DAY
GROUP BY repo_name
"""

_TOP_REPOS_ALL_QUERY = (
    """
SELECT
    rm.repo_id AS repo_id,
    rm.repo_full_name AS repo_full_name,
    rm.repo_name AS repo_name,
    rm.html_url AS html_url,
    rm.description AS description,
    rm.primary_language AS primary_language,
    rm.topics AS topics,
    rm.category AS category,
    rm.stargazers_count AS stargazers_count,
    rm.watchers_count AS watchers_count,
    rm.forks_count AS forks_count,
    rm.open_issues_count AS open_issues_count,
    rm.subscribers_count AS subscribers_count,
    rm.owner_login AS owner_login,
    rm.owner_avatar_url AS owner_avatar_url,
    rm.license_name AS license_name,
    rm.github_created_at AS github_created_at,
    greatest(rm.github_pushed_at, coalesce(metrics.latest_event_at, rm.github_pushed_at))
        AS github_pushed_at,
    rm.rank AS rank,
    coalesce(metrics.star_count_in_window, 0) AS star_count_in_window
FROM repo_metadata AS rm
FINAL
INNER JOIN (
    """
    + _REPO_WINDOW_METRICS_SUBQUERY
    + """
) AS metrics
    ON metrics.repo_name = rm.repo_full_name
ORDER BY star_count_in_window DESC, rm.stargazers_count DESC
LIMIT %(limit)s
"""
)

_TOP_REPOS_CATEGORY_QUERY = (
    """
SELECT
    rm.repo_id AS repo_id,
    rm.repo_full_name AS repo_full_name,
    rm.repo_name AS repo_name,
    rm.html_url AS html_url,
    rm.description AS description,
    rm.primary_language AS primary_language,
    rm.topics AS topics,
    rm.category AS category,
    rm.stargazers_count AS stargazers_count,
    rm.watchers_count AS watchers_count,
    rm.forks_count AS forks_count,
    rm.open_issues_count AS open_issues_count,
    rm.subscribers_count AS subscribers_count,
    rm.owner_login AS owner_login,
    rm.owner_avatar_url AS owner_avatar_url,
    rm.license_name AS license_name,
    rm.github_created_at AS github_created_at,
    greatest(rm.github_pushed_at, coalesce(metrics.latest_event_at, rm.github_pushed_at))
        AS github_pushed_at,
    rm.rank AS rank,
    coalesce(metrics.star_count_in_window, 0) AS star_count_in_window
FROM repo_metadata AS rm
FINAL
INNER JOIN (
    """
    + _REPO_WINDOW_METRICS_SUBQUERY
    + """
) AS metrics
    ON metrics.repo_name = rm.repo_full_name
WHERE rm.category = %(category)s
ORDER BY star_count_in_window DESC, rm.stargazers_count DESC
LIMIT %(limit)s
"""
)

_TOP_STARRED_REPOS_ALL_QUERY = """
SELECT
    rm.repo_id AS repo_id,
    rm.repo_full_name AS repo_full_name,
    rm.repo_name AS repo_name,
    rm.html_url AS html_url,
    rm.description AS description,
    rm.primary_language AS primary_language,
    rm.topics AS topics,
    rm.category AS category,
    rm.stargazers_count AS stargazers_count,
    rm.watchers_count AS watchers_count,
    rm.forks_count AS forks_count,
    rm.open_issues_count AS open_issues_count,
    rm.subscribers_count AS subscribers_count,
    rm.owner_login AS owner_login,
    rm.owner_avatar_url AS owner_avatar_url,
    rm.license_name AS license_name,
    rm.github_created_at AS github_created_at,
    rm.github_pushed_at AS github_pushed_at,
    rm.rank AS rank,
    toInt64(0) AS star_count_in_window
FROM repo_metadata AS rm
FINAL
ORDER BY rm.stargazers_count DESC, rm.repo_full_name ASC
LIMIT %(limit)s
"""

_TOP_STARRED_REPOS_CATEGORY_QUERY = """
SELECT
    rm.repo_id AS repo_id,
    rm.repo_full_name AS repo_full_name,
    rm.repo_name AS repo_name,
    rm.html_url AS html_url,
    rm.description AS description,
    rm.primary_language AS primary_language,
    rm.topics AS topics,
    rm.category AS category,
    rm.stargazers_count AS stargazers_count,
    rm.watchers_count AS watchers_count,
    rm.forks_count AS forks_count,
    rm.open_issues_count AS open_issues_count,
    rm.subscribers_count AS subscribers_count,
    rm.owner_login AS owner_login,
    rm.owner_avatar_url AS owner_avatar_url,
    rm.license_name AS license_name,
    rm.github_created_at AS github_created_at,
    rm.github_pushed_at AS github_pushed_at,
    rm.rank AS rank,
    toInt64(0) AS star_count_in_window
FROM repo_metadata AS rm
FINAL
WHERE rm.category = %(category)s
ORDER BY rm.stargazers_count DESC, rm.repo_full_name ASC
LIMIT %(limit)s
"""

_TRENDING_QUERY = """
WITH
    latest AS (
        SELECT
            repo_full_name,
            argMax(repo_id, snapshot_at) AS repo_id,
            argMax(repo_name, snapshot_at) AS repo_name,
            argMax(html_url, snapshot_at) AS html_url,
            argMax(description, snapshot_at) AS description,
            argMax(primary_language, snapshot_at) AS primary_language,
            argMax(topics, snapshot_at) AS topics,
            argMax(category, snapshot_at) AS category,
            argMax(stargazers_count, snapshot_at) AS stargazers_count,
            argMax(watchers_count, snapshot_at) AS watchers_count,
            argMax(forks_count, snapshot_at) AS forks_count,
            argMax(open_issues_count, snapshot_at) AS open_issues_count,
            argMax(subscribers_count, snapshot_at) AS subscribers_count,
            argMax(owner_login, snapshot_at) AS owner_login,
            argMax(owner_avatar_url, snapshot_at) AS owner_avatar_url,
            argMax(license_name, snapshot_at) AS license_name,
            argMax(github_created_at, snapshot_at) AS github_created_at,
            argMax(github_pushed_at, snapshot_at) AS github_pushed_at,
            argMax(rank, snapshot_at) AS rank
        FROM repo_metadata_history
        FINAL
        WHERE snapshot_at < %(week_end)s
        GROUP BY repo_full_name
    ),
    before_week AS (
        SELECT
            repo_full_name,
            argMax(stargazers_count, snapshot_at) AS baseline_stars
        FROM repo_metadata_history
        FINAL
        WHERE snapshot_at < %(week_start)s
        GROUP BY repo_full_name
    ),
    first_week AS (
        SELECT
            repo_full_name,
            argMin(stargazers_count, snapshot_at) AS first_week_stars
        FROM repo_metadata_history
        FINAL
        WHERE snapshot_at >= %(week_start)s
          AND snapshot_at < %(week_end)s
        GROUP BY repo_full_name
    )
SELECT
    repo_id,
    repo_full_name,
    repo_name,
    html_url,
    description,
    primary_language,
    topics,
    category,
    stargazers_count,
    watchers_count,
    forks_count,
    open_issues_count,
    subscribers_count,
    owner_login,
    owner_avatar_url,
    license_name,
    github_created_at,
    github_pushed_at,
    rank,
    star_count_in_window
FROM (
    SELECT
        latest.*,
        greatest(
            latest.stargazers_count - coalesce(
                before_week.baseline_stars,
                first_week.first_week_stars,
                latest.stargazers_count
            ),
            0
        ) AS star_count_in_window
    FROM latest
    LEFT JOIN before_week ON before_week.repo_full_name = latest.repo_full_name
    LEFT JOIN first_week ON first_week.repo_full_name = latest.repo_full_name
) AS weekly_growth
WHERE star_count_in_window > 0
ORDER BY star_count_in_window DESC, stargazers_count DESC
LIMIT %(limit)s
"""

_TOPIC_BREAKDOWN_QUERY = """
SELECT
    topic,
    countIf(gd.event_type = 'WatchEvent') AS event_count,
    COUNT(DISTINCT gd.repo_name) AS repo_count
FROM github_analyzer.github_data AS gd
ARRAY JOIN gd.repo_topics AS topic
WHERE gd.created_at >= now() - INTERVAL %(days)s DAY
  AND topic != ''
GROUP BY topic
HAVING event_count > 0
ORDER BY event_count DESC
LIMIT 30
"""

_LANGUAGE_BREAKDOWN_QUERY = """
SELECT
    gd.repo_primary_language AS language,
    countIf(gd.event_type = 'WatchEvent') AS event_count,
    COUNT(DISTINCT gd.repo_name) AS repo_count
FROM github_analyzer.github_data AS gd
WHERE gd.created_at >= now() - INTERVAL %(days)s DAY
  AND gd.repo_primary_language != ''
GROUP BY gd.repo_primary_language
HAVING event_count > 0
ORDER BY event_count DESC
LIMIT 20
"""

_REPO_TIMESERIES_QUERY = """
SELECT
    toDate(ge.created_at) AS event_date,
    countIf(ge.event_type = 'WatchEvent') AS star_count,
    count() AS total_events
FROM github_analyzer.github_data AS ge
WHERE ge.repo_name = %(repo_name)s
  AND ge.created_at >= now() - INTERVAL %(days)s DAY
GROUP BY event_date
ORDER BY event_date ASC
"""

_CATEGORY_SUMMARY_QUERY = """
SELECT
    rm.category AS category,
    count() AS repo_count,
    SUM(rm.stargazers_count) AS total_stars,
    argMax(rm.repo_full_name, rm.stargazers_count) AS top_repo_name,
    MAX(rm.stargazers_count) AS top_repo_stars,
    coalesce(SUM(metrics.star_count_in_window), 0) AS weekly_star_delta
FROM repo_metadata AS rm
FINAL
LEFT JOIN (
    SELECT
        repo_name,
        countIf(event_type = 'WatchEvent') AS star_count_in_window
    FROM github_data
    WHERE created_at >= now() - INTERVAL 7 DAY
    GROUP BY repo_name
) AS metrics
    ON metrics.repo_name = rm.repo_full_name
GROUP BY rm.category
ORDER BY total_stars DESC
"""

_MOVER_METRICS_SUBQUERY = """
SELECT
    repo_name,
    countIf(
        event_type = 'WatchEvent'
        AND created_at >= now() - INTERVAL %(days)s DAY
    ) AS current_star_count,
    countIf(
        event_type = 'WatchEvent'
        AND created_at < now() - INTERVAL %(days)s DAY
        AND created_at >= now() - INTERVAL %(days_twice)s DAY
    ) AS previous_star_count,
    uniqExactIf(
        actor_login,
        created_at >= now() - INTERVAL %(days)s DAY
    ) AS unique_actors_in_window,
    max(created_at) AS latest_event_at
FROM github_analyzer.github_data
WHERE created_at >= now() - INTERVAL %(days_twice)s DAY
GROUP BY repo_name
HAVING current_star_count > 0
"""

_SHOCK_MOVERS_ABSOLUTE_QUERY = (
    """
SELECT
    rm.repo_id AS repo_id,
    rm.repo_full_name AS repo_full_name,
    rm.repo_name AS repo_name,
    rm.html_url AS html_url,
    rm.description AS description,
    rm.primary_language AS primary_language,
    rm.topics AS topics,
    rm.category AS category,
    rm.stargazers_count AS stargazers_count,
    rm.watchers_count AS watchers_count,
    rm.forks_count AS forks_count,
    rm.open_issues_count AS open_issues_count,
    rm.subscribers_count AS subscribers_count,
    rm.owner_login AS owner_login,
    rm.owner_avatar_url AS owner_avatar_url,
    rm.license_name AS license_name,
    rm.github_created_at AS github_created_at,
    greatest(rm.github_pushed_at, coalesce(metrics.latest_event_at, rm.github_pushed_at))
        AS github_pushed_at,
    rm.rank AS rank,
    metrics.current_star_count AS star_count_in_window,
    metrics.previous_star_count AS previous_star_count_in_window,
    metrics.unique_actors_in_window AS unique_actors_in_window,
    round(
        (
            metrics.current_star_count
            / greatest(rm.stargazers_count - metrics.current_star_count, 1)
        ) * 100,
        2
    ) AS weekly_percent_gain,
    round(metrics.current_star_count / greatest(metrics.previous_star_count, 1), 4)
        AS window_over_window_ratio
FROM repo_metadata AS rm
FINAL
INNER JOIN (
    """
    + _MOVER_METRICS_SUBQUERY
    + """
) AS metrics
    ON metrics.repo_name = rm.repo_full_name
ORDER BY
    metrics.current_star_count DESC,
    metrics.unique_actors_in_window DESC,
    rm.stargazers_count DESC
LIMIT %(limit)s
"""
)

_SHOCK_MOVERS_PERCENTAGE_QUERY = (
    """
SELECT
    rm.repo_id AS repo_id,
    rm.repo_full_name AS repo_full_name,
    rm.repo_name AS repo_name,
    rm.html_url AS html_url,
    rm.description AS description,
    rm.primary_language AS primary_language,
    rm.topics AS topics,
    rm.category AS category,
    rm.stargazers_count AS stargazers_count,
    rm.watchers_count AS watchers_count,
    rm.forks_count AS forks_count,
    rm.open_issues_count AS open_issues_count,
    rm.subscribers_count AS subscribers_count,
    rm.owner_login AS owner_login,
    rm.owner_avatar_url AS owner_avatar_url,
    rm.license_name AS license_name,
    rm.github_created_at AS github_created_at,
    greatest(rm.github_pushed_at, coalesce(metrics.latest_event_at, rm.github_pushed_at))
        AS github_pushed_at,
    rm.rank AS rank,
    metrics.current_star_count AS star_count_in_window,
    metrics.previous_star_count AS previous_star_count_in_window,
    metrics.unique_actors_in_window AS unique_actors_in_window,
    round(
        (
            metrics.current_star_count
            / greatest(rm.stargazers_count - metrics.current_star_count, 1)
        ) * 100,
        2
    ) AS weekly_percent_gain,
    round(metrics.current_star_count / greatest(metrics.previous_star_count, 1), 4)
        AS window_over_window_ratio
FROM repo_metadata AS rm
FINAL
INNER JOIN (
    """
    + _MOVER_METRICS_SUBQUERY
    + """
) AS metrics
    ON metrics.repo_name = rm.repo_full_name
WHERE greatest(rm.stargazers_count - metrics.current_star_count, 0) >= %(min_baseline_stars)s
ORDER BY
    weekly_percent_gain DESC,
    metrics.current_star_count DESC,
    metrics.unique_actors_in_window DESC
LIMIT %(limit)s
"""
)

_TOPIC_ROTATION_QUERY = """
SELECT
    topic,
    countIf(
        event_type = 'WatchEvent'
        AND created_at >= now() - INTERVAL %(days)s DAY
    ) AS current_star_count,
    countIf(
        event_type = 'WatchEvent'
        AND created_at < now() - INTERVAL %(days)s DAY
        AND created_at >= now() - INTERVAL %(days_twice)s DAY
    ) AS previous_star_count,
    uniqExactIf(
        repo_name,
        created_at >= now() - INTERVAL %(days)s DAY
    ) AS repo_count
FROM (
    SELECT
        created_at,
        event_type,
        repo_name,
        arrayJoin(repo_topics) AS topic
    FROM github_analyzer.github_data
    WHERE created_at >= now() - INTERVAL %(days_twice)s DAY
) AS topic_events
WHERE topic != ''
GROUP BY topic
HAVING current_star_count > 0
ORDER BY
    (current_star_count - previous_star_count) DESC,
    current_star_count DESC,
    repo_count DESC
LIMIT %(limit)s
"""


class ClickHouseDashboardService:
    """Executes analytical ClickHouse queries for dashboard serving."""

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
        self._classifier = CategoryClassifier()
        self._has_categorized_metadata_cache: bool | None = None

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

    def _execute_query(
        self,
        query: str,
        params: dict[str, Any] | None = None,
    ) -> list[tuple[Any, ...]]:
        client = self._get_client()
        try:
            rows = client.execute(query, params or {})
            return cast("list[tuple[Any, ...]]", rows)
        except ClickHouseError as exc:
            raise DashboardQueryError(f"Dashboard query failed: {exc}") from exc

    def _repo_metadata_table_exists(self) -> bool:
        rows = self._execute_query("EXISTS TABLE github_analyzer.repo_metadata")
        if not rows or not rows[0]:
            return False
        try:
            return int(rows[0][0]) == 1
        except TypeError, ValueError:
            return True

    def _repo_metadata_history_table_exists(self) -> bool:
        rows = self._execute_query("EXISTS TABLE github_analyzer.repo_metadata_history")
        if not rows or not rows[0]:
            return False
        try:
            return int(rows[0][0]) == 1
        except TypeError, ValueError:
            return True

    def _require_repo_metadata(self) -> None:
        if not self._repo_metadata_table_exists():
            raise DashboardQueryError("Dashboard query failed: repo_metadata table is required")

    def _require_repo_metadata_history(self) -> None:
        if not self._repo_metadata_history_table_exists():
            raise DashboardQueryError(
                "Dashboard query failed: repo_metadata_history table is required"
            )

    def _has_categorized_repo_metadata(self) -> bool:
        if self._has_categorized_metadata_cache is not None:
            return self._has_categorized_metadata_cache

        self._require_repo_metadata()
        rows = self._execute_query(
            """
SELECT countIf(category != 'Other')
FROM github_analyzer.repo_metadata
FINAL
""",
        )
        try:
            self._has_categorized_metadata_cache = int(rows[0][0]) > 0
        except IndexError, TypeError, ValueError:
            self._has_categorized_metadata_cache = True
        return self._has_categorized_metadata_cache

    @staticmethod
    def _current_gmt7_week_bounds(now: datetime | None = None) -> tuple[datetime, datetime]:
        current_utc = now or datetime.now(tz=UTC)
        local_now = current_utc.astimezone(_GMT7)
        week_start_local = datetime.combine(
            local_now.date() - timedelta(days=local_now.weekday()),
            datetime.min.time(),
            tzinfo=_GMT7,
        )
        return week_start_local.astimezone(UTC), current_utc

    @staticmethod
    def _parse_repo_row(row: tuple[Any, ...]) -> dict[str, Any]:
        topics_raw = row[6]
        topics: list[str] = list(topics_raw) if topics_raw else []
        raw_category = str(row[7])
        effective_category = raw_category
        if raw_category == RepoCategory.OTHER.value:
            effective_category = str(
                CategoryClassifier().classify(
                    topics=topics,
                    description=str(row[4]),
                )
            )
        return {
            "repo_id": int(row[0]),
            "repo_full_name": str(row[1]),
            "repo_name": str(row[2]),
            "html_url": str(row[3]),
            "description": str(row[4]),
            "primary_language": str(row[5]),
            "topics": topics,
            "category": effective_category,
            "stargazers_count": int(row[8]),
            "watchers_count": int(row[9]),
            "forks_count": int(row[10]),
            "open_issues_count": int(row[11]),
            "subscribers_count": int(row[12]),
            "owner_login": str(row[13]),
            "owner_avatar_url": str(row[14]),
            "license_name": str(row[15]),
            "github_created_at": row[16],
            "github_pushed_at": row[17],
            "rank": int(row[18]),
            "star_count_in_window": int(row[19]),
        }

    @staticmethod
    def _parse_mover_row(row: tuple[Any, ...], *, rank: int) -> dict[str, Any]:
        item = ClickHouseDashboardService._parse_repo_row(row)
        item["previous_star_count_in_window"] = int(row[20])
        item["unique_actors_in_window"] = int(row[21])
        item["weekly_percent_gain"] = round(float(row[22]), 2)
        item["window_over_window_ratio"] = round(float(row[23]), 4)
        item["rank"] = rank
        return item

    @staticmethod
    def _apply_category_filter(
        items: list[dict[str, Any]],
        *,
        category: str | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        if category is None:
            return items[:limit]
        return [item for item in items if item["category"] == category][:limit]

    async def get_top_repos(
        self,
        category: str | None,
        days: int,
        limit: int,
    ) -> list[dict[str, Any]]:
        self._has_categorized_repo_metadata()
        params: dict[str, Any] = {"days": days, "limit": limit}
        query = _TOP_REPOS_CATEGORY_QUERY if category else _TOP_REPOS_ALL_QUERY
        if category:
            params["category"] = category

        def _run() -> list[dict[str, Any]]:
            rows = self._execute_query(query, params)
            items = [self._parse_repo_row(r) for r in rows]
            return self._apply_category_filter(items, category=category, limit=limit)

        return await asyncio.to_thread(_run)

    async def get_top_starred_repos(
        self,
        category: str | None,
        limit: int,
        days: int = 7,
    ) -> list[dict[str, Any]]:
        del days
        self._has_categorized_repo_metadata()
        params: dict[str, Any] = {"limit": limit}
        query = _TOP_STARRED_REPOS_CATEGORY_QUERY if category else _TOP_STARRED_REPOS_ALL_QUERY
        if category:
            params["category"] = category

        def _run() -> list[dict[str, Any]]:
            rows = self._execute_query(query, params)
            items = [self._parse_repo_row(r) for r in rows]
            return self._apply_category_filter(items, category=category, limit=limit)

        return await asyncio.to_thread(_run)

    async def get_trending(self, days: int, limit: int) -> list[dict[str, Any]]:
        del days
        week_start, week_end = self._current_gmt7_week_bounds()
        self._require_repo_metadata_history()
        params: dict[str, Any] = {
            "week_start": week_start,
            "week_end": week_end,
            "limit": limit,
        }

        def _run() -> list[dict[str, Any]]:
            rows = self._execute_query(_TRENDING_QUERY, params)
            results = []
            for rank, row in enumerate(rows, start=1):
                item = self._parse_repo_row(row)
                item["growth_rank"] = rank
                results.append(item)
            return results

        return await asyncio.to_thread(_run)

    async def get_shock_movers(
        self,
        *,
        days: int,
        absolute_limit: int,
        percentage_limit: int,
        min_baseline_stars: int,
    ) -> dict[str, Any]:
        self._require_repo_metadata()
        params: dict[str, Any] = {
            "days": days,
            "days_twice": max(days * 2, 2),
            "min_baseline_stars": min_baseline_stars,
        }

        def _run() -> dict[str, Any]:
            absolute_rows = self._execute_query(
                _SHOCK_MOVERS_ABSOLUTE_QUERY,
                {**params, "limit": absolute_limit},
            )
            percentage_rows = self._execute_query(
                _SHOCK_MOVERS_PERCENTAGE_QUERY,
                {**params, "limit": percentage_limit},
            )
            return {
                "window_days": days,
                "absolute_movers": [
                    self._parse_mover_row(row, rank=rank)
                    for rank, row in enumerate(absolute_rows, start=1)
                ],
                "percentage_movers": [
                    self._parse_mover_row(row, rank=rank)
                    for rank, row in enumerate(percentage_rows, start=1)
                ],
            }

        return await asyncio.to_thread(_run)

    async def get_topic_rotation(self, *, days: int, limit: int) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"days": days, "days_twice": max(days * 2, 2), "limit": limit}

        def _run() -> list[dict[str, Any]]:
            rows = self._execute_query(_TOPIC_ROTATION_QUERY, params)
            return [
                {
                    "topic": str(row[0]),
                    "current_star_count": int(row[1]),
                    "previous_star_count": int(row[2]),
                    "star_delta": int(row[1]) - int(row[2]),
                    "repo_count": int(row[3]),
                    "rank": rank,
                }
                for rank, row in enumerate(rows, start=1)
            ]

        return await asyncio.to_thread(_run)

    async def get_topic_breakdown(self, days: int) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"days": days}

        def _run() -> list[dict[str, Any]]:
            rows = self._execute_query(_TOPIC_BREAKDOWN_QUERY, params)
            return [
                {
                    "topic": str(row[0]),
                    "event_count": int(row[1]),
                    "repo_count": int(row[2]),
                }
                for row in rows
            ]

        return await asyncio.to_thread(_run)

    async def get_language_breakdown(self, days: int) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"days": days}

        def _run() -> list[dict[str, Any]]:
            rows = self._execute_query(_LANGUAGE_BREAKDOWN_QUERY, params)
            return [
                {
                    "language": str(row[0]),
                    "event_count": int(row[1]),
                    "repo_count": int(row[2]),
                }
                for row in rows
            ]

        return await asyncio.to_thread(_run)

    async def get_repo_timeseries(self, repo_name: str, days: int) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"repo_name": repo_name, "days": days}

        def _run() -> list[dict[str, Any]]:
            rows = self._execute_query(_REPO_TIMESERIES_QUERY, params)
            return [
                {
                    "event_date": row[0],
                    "star_count": int(row[1]),
                    "total_events": int(row[2]),
                }
                for row in rows
            ]

        return await asyncio.to_thread(_run)

    async def get_category_summary(self) -> list[dict[str, Any]]:
        self._has_categorized_repo_metadata()

        def _run() -> list[dict[str, Any]]:
            rows = self._execute_query(_CATEGORY_SUMMARY_QUERY)
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

        return await asyncio.to_thread(_run)
