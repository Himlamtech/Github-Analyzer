"""ClickHouse-backed dashboard query service with Parquet fallback."""

from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any, cast

import pyarrow.parquet as pq
from clickhouse_driver import Client
from clickhouse_driver.errors import Error as ClickHouseDriverError
from clickhouse_driver.errors import NetworkError as ClickHouseDriverNetworkError

from src.domain.exceptions import ClickHouseConnectionError, DashboardQueryError

_TOP_REPOS_QUERY = """
SELECT
    rm.repo_id,
    rm.repo_full_name,
    rm.repo_name,
    rm.html_url,
    rm.description,
    rm.primary_language,
    rm.topics,
    rm.category,
    rm.stargazers_count,
    rm.watchers_count,
    rm.forks_count,
    rm.open_issues_count,
    rm.subscribers_count,
    rm.owner_login,
    rm.owner_avatar_url,
    rm.license_name,
    rm.github_created_at,
    rm.github_pushed_at,
    rm.rank,
    coalesce(metrics.star_count_in_window, 0) AS star_count_in_window
FROM repo_metadata AS rm
FINAL
LEFT JOIN (
    SELECT
        repo_name,
        sum(star_count) AS star_count_in_window
    FROM repo_star_counts
    WHERE event_date >= today() - %(days)s
    GROUP BY repo_name
) AS metrics
    ON metrics.repo_name = rm.repo_full_name
WHERE (%(category)s = '' OR rm.category = %(category)s)
ORDER BY rm.stargazers_count DESC, star_count_in_window DESC, rm.github_pushed_at DESC
LIMIT %(limit)s
"""

_TOP_REPOS_ALL_FALLBACK_QUERY = """
SELECT
    any(repo_id) AS repo_id,
    normalized_repo_name AS repo_full_name,
    splitByChar('/', normalized_repo_name)[2] AS repo_name,
    concat('https://github.com/', normalized_repo_name) AS html_url,
    any(repo_description) AS description,
    any(repo_primary_language) AS primary_language,
    any(repo_topics) AS topics,
    'Other' AS category,
    max(repo_stargazers_count) AS stargazers_count,
    max(repo_stargazers_count) AS watchers_count,
    toInt64(0) AS forks_count,
    toInt64(0) AS open_issues_count,
    toInt64(0) AS subscribers_count,
    splitByChar('/', normalized_repo_name)[1] AS owner_login,
    '' AS owner_avatar_url,
    '' AS license_name,
    min(created_at) AS github_created_at,
    max(created_at) AS github_pushed_at,
    toInt32(0) AS rank,
    countIf(event_type = 'WatchEvent' AND created_at >= now() - INTERVAL %(days)s DAY)
        AS star_count_in_window
FROM (
    SELECT
        *,
        lowerUTF8(repo_name) AS normalized_repo_name
    FROM github_analyzer.github_data
) AS raw
GROUP BY normalized_repo_name
ORDER BY stargazers_count DESC, star_count_in_window DESC, github_pushed_at DESC
LIMIT %(limit)s
"""

_TOP_REPOS_CATEGORY_FALLBACK_QUERY = """
SELECT
    any(repo_id) AS repo_id,
    normalized_repo_name AS repo_full_name,
    splitByChar('/', normalized_repo_name)[2] AS repo_name,
    concat('https://github.com/', normalized_repo_name) AS html_url,
    any(repo_description) AS description,
    any(repo_primary_language) AS primary_language,
    any(repo_topics) AS topics,
    'Other' AS category,
    max(repo_stargazers_count) AS stargazers_count,
    max(repo_stargazers_count) AS watchers_count,
    toInt64(0) AS forks_count,
    toInt64(0) AS open_issues_count,
    toInt64(0) AS subscribers_count,
    splitByChar('/', normalized_repo_name)[1] AS owner_login,
    '' AS owner_avatar_url,
    '' AS license_name,
    min(created_at) AS github_created_at,
    max(created_at) AS github_pushed_at,
    toInt32(0) AS rank,
    countIf(event_type = 'WatchEvent' AND created_at >= now() - INTERVAL %(days)s DAY)
        AS star_count_in_window
FROM (
    SELECT
        *,
        lowerUTF8(repo_name) AS normalized_repo_name
    FROM github_analyzer.github_data
) AS raw
GROUP BY normalized_repo_name
HAVING (%(category)s = '' OR %(category)s = 'Other')
ORDER BY stargazers_count DESC, star_count_in_window DESC, github_pushed_at DESC
LIMIT %(limit)s
"""

_TRENDING_QUERY = """
SELECT
    rm.repo_id,
    rm.repo_full_name,
    rm.repo_name,
    rm.html_url,
    rm.description,
    rm.primary_language,
    rm.topics,
    rm.category,
    rm.stargazers_count,
    rm.watchers_count,
    rm.forks_count,
    rm.open_issues_count,
    rm.subscribers_count,
    rm.owner_login,
    rm.owner_avatar_url,
    rm.license_name,
    rm.github_created_at,
    rm.github_pushed_at,
    rm.rank,
    coalesce(metrics.star_count_in_window, 0) AS star_count_in_window
FROM repo_metadata AS rm
FINAL
INNER JOIN (
    SELECT
        repo_name,
        sum(star_count) AS star_count_in_window
    FROM repo_star_counts
    WHERE event_date >= today() - %(days)s
    GROUP BY repo_name
) AS metrics
    ON metrics.repo_name = rm.repo_full_name
ORDER BY star_count_in_window DESC, rm.stargazers_count DESC, rm.github_pushed_at DESC
LIMIT %(limit)s
"""

_TRENDING_FALLBACK_QUERY = """
SELECT
    any(repo_id) AS repo_id,
    normalized_repo_name AS repo_full_name,
    splitByChar('/', normalized_repo_name)[2] AS repo_name,
    concat('https://github.com/', normalized_repo_name) AS html_url,
    any(repo_description) AS description,
    any(repo_primary_language) AS primary_language,
    any(repo_topics) AS topics,
    'Other' AS category,
    max(repo_stargazers_count) AS stargazers_count,
    max(repo_stargazers_count) AS watchers_count,
    toInt64(0) AS forks_count,
    toInt64(0) AS open_issues_count,
    toInt64(0) AS subscribers_count,
    splitByChar('/', normalized_repo_name)[1] AS owner_login,
    '' AS owner_avatar_url,
    '' AS license_name,
    min(created_at) AS github_created_at,
    max(created_at) AS github_pushed_at,
    toInt32(0) AS rank,
    countIf(event_type = 'WatchEvent' AND created_at >= now() - INTERVAL %(days)s DAY)
        AS star_count_in_window
FROM (
    SELECT
        *,
        lowerUTF8(repo_name) AS normalized_repo_name
    FROM github_analyzer.github_data
) AS raw
GROUP BY normalized_repo_name
ORDER BY star_count_in_window DESC, stargazers_count DESC, github_pushed_at DESC
LIMIT %(limit)s
"""

_LANGUAGE_BREAKDOWN_QUERY = """
SELECT
    if(repo_primary_language = '', 'Unknown', repo_primary_language) AS language,
    countIf(event_type = 'WatchEvent') AS star_count,
    uniqExact(lowerUTF8(repo_name)) AS repo_count
FROM github_analyzer.github_data
WHERE created_at >= now() - INTERVAL %(days)s DAY
GROUP BY language
ORDER BY star_count DESC, repo_count DESC, language ASC
LIMIT %(limit)s
"""

_TOPIC_BREAKDOWN_QUERY = """
SELECT
    topic,
    countIf(event_type = 'WatchEvent') AS star_count,
    uniqExact(lowerUTF8(repo_name)) AS repo_count
FROM github_analyzer.github_data
ARRAY JOIN repo_topics AS topic
WHERE created_at >= now() - INTERVAL %(days)s DAY
  AND topic != ''
GROUP BY topic
ORDER BY star_count DESC, repo_count DESC, topic ASC
LIMIT %(limit)s
"""

_REPO_TIMESERIES_QUERY = """
SELECT
    toDate(created_at) AS event_date,
    countIf(event_type = 'WatchEvent') AS star_count,
    count() AS total_events
FROM github_analyzer.github_data
WHERE lowerUTF8(repo_name) = lowerUTF8(%(repo_name)s)
  AND created_at >= now() - INTERVAL %(days)s DAY
GROUP BY event_date
ORDER BY event_date ASC
"""

_CATEGORY_SUMMARY_QUERY = """
SELECT
    rm.category AS category,
    count() AS repo_count,
    sum(rm.stargazers_count) AS total_stars,
    argMax(rm.repo_full_name, rm.stargazers_count) AS top_repo_name,
    max(rm.stargazers_count) AS top_repo_stars,
    sum(coalesce(metrics.star_count_in_window, 0)) AS weekly_star_delta
FROM repo_metadata AS rm
FINAL
LEFT JOIN (
    SELECT
        repo_name,
        sum(star_count) AS star_count_in_window
    FROM repo_star_counts
    WHERE event_date >= today() - %(days)s
    GROUP BY repo_name
) AS metrics
    ON metrics.repo_name = rm.repo_full_name
GROUP BY rm.category
ORDER BY weekly_star_delta DESC, total_stars DESC, repo_count DESC
LIMIT %(limit)s
"""

_CATEGORY_SUMMARY_FALLBACK_QUERY = """
SELECT
    topic AS category,
    uniqExact(normalized_repo_name) AS repo_count,
    sum(repo_peak_stars) AS total_stars,
    argMax(normalized_repo_name, repo_peak_stars) AS top_repo_name,
    max(repo_peak_stars) AS top_repo_stars,
    sum(window_star_count) AS weekly_star_delta
FROM (
    SELECT
        normalized_repo_name,
        topic,
        max(repo_stargazers_count) AS repo_peak_stars,
        countIf(event_type = 'WatchEvent' AND created_at >= now() - INTERVAL %(days)s DAY)
            AS window_star_count
    FROM (
        SELECT
            lowerUTF8(repo_name) AS normalized_repo_name,
            repo_stargazers_count,
            created_at,
            event_type,
            arrayJoin(
                if(length(repo_topics) = 0, ['Other'], arrayMap(x -> lowerUTF8(x), repo_topics))
            ) AS topic
        FROM github_analyzer.github_data
    ) AS expanded
    GROUP BY normalized_repo_name, topic
)
GROUP BY category
ORDER BY weekly_star_delta DESC, total_stars DESC, repo_count DESC
LIMIT %(limit)s
"""

_SHOCK_MOVERS_QUERY = """
SELECT
    rm.repo_id,
    rm.repo_full_name,
    rm.repo_name,
    rm.html_url,
    rm.description,
    rm.primary_language,
    rm.topics,
    rm.category,
    rm.stargazers_count,
    rm.watchers_count,
    rm.forks_count,
    rm.open_issues_count,
    rm.subscribers_count,
    rm.owner_login,
    rm.owner_avatar_url,
    rm.license_name,
    rm.github_created_at,
    rm.github_pushed_at,
    rm.rank,
    metrics.star_count_in_window,
    metrics.previous_star_count_in_window,
    metrics.unique_actors_in_window
FROM repo_metadata AS rm
FINAL
INNER JOIN (
    SELECT
        normalized_repo_name AS repo_full_name,
        countIf(event_type = 'WatchEvent' AND created_at >= now() - INTERVAL %(days)s DAY)
            AS star_count_in_window,
        countIf(
            event_type = 'WatchEvent'
            AND created_at < now() - INTERVAL %(days)s DAY
            AND created_at >= now() - INTERVAL %(days_twice)s DAY
        ) AS previous_star_count_in_window,
        uniqExactIf(actor_login, created_at >= now() - INTERVAL %(days)s DAY)
            AS unique_actors_in_window
    FROM (
        SELECT
            *,
            lowerUTF8(repo_name) AS normalized_repo_name
        FROM github_analyzer.github_data
    ) AS raw
    GROUP BY normalized_repo_name
    HAVING star_count_in_window > 0
) AS metrics
    ON metrics.repo_full_name = rm.repo_full_name
ORDER BY metrics.star_count_in_window DESC, rm.stargazers_count DESC, rm.github_pushed_at DESC
"""

_SHOCK_MOVERS_FALLBACK_QUERY = """
SELECT
    any(repo_id) AS repo_id,
    normalized_repo_name AS repo_full_name,
    splitByChar('/', normalized_repo_name)[2] AS repo_name,
    concat('https://github.com/', normalized_repo_name) AS html_url,
    any(repo_description) AS description,
    any(repo_primary_language) AS primary_language,
    any(repo_topics) AS topics,
    'Other' AS category,
    max(repo_stargazers_count) AS stargazers_count,
    max(repo_stargazers_count) AS watchers_count,
    toInt64(0) AS forks_count,
    toInt64(0) AS open_issues_count,
    toInt64(0) AS subscribers_count,
    splitByChar('/', normalized_repo_name)[1] AS owner_login,
    '' AS owner_avatar_url,
    '' AS license_name,
    min(created_at) AS github_created_at,
    max(created_at) AS github_pushed_at,
    toInt32(0) AS rank,
    countIf(event_type = 'WatchEvent' AND created_at >= now() - INTERVAL %(days)s DAY)
        AS star_count_in_window,
    countIf(
        event_type = 'WatchEvent'
        AND created_at < now() - INTERVAL %(days)s DAY
        AND created_at >= now() - INTERVAL %(days_twice)s DAY
    ) AS previous_star_count_in_window,
    uniqExactIf(actor_login, created_at >= now() - INTERVAL %(days)s DAY)
        AS unique_actors_in_window
FROM (
    SELECT
        *,
        lowerUTF8(repo_name) AS normalized_repo_name
    FROM github_analyzer.github_data
) AS raw
GROUP BY normalized_repo_name
HAVING star_count_in_window > 0
"""

_TOPIC_ROTATION_QUERY = """
SELECT
    topic,
    countIf(event_type = 'WatchEvent' AND created_at >= now() - INTERVAL %(days)s DAY)
        AS current_star_count,
    countIf(
        event_type = 'WatchEvent'
        AND created_at < now() - INTERVAL %(days)s DAY
        AND created_at >= now() - INTERVAL %(days_twice)s DAY
    ) AS previous_star_count,
    uniqExactIf(lowerUTF8(repo_name), created_at >= now() - INTERVAL %(days)s DAY)
        AS repo_count
FROM github_analyzer.github_data
ARRAY JOIN repo_topics AS topic
WHERE topic != ''
GROUP BY topic
HAVING current_star_count > 0
ORDER BY current_star_count DESC, repo_count DESC, topic ASC
LIMIT %(limit)s
"""


class ClickHouseDashboardService:
    """Storage-backed service for dashboard analytics."""

    def __init__(
        self,
        *,
        host: str,
        port: int,
        user: str,
        password: str,
        database: str,
        parquet_base_path: str,
    ) -> None:
        self._host = host
        self._port = port
        self._user = user
        self._password = password
        self._database = database
        self._parquet_base_path = parquet_base_path

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
        except ClickHouseDriverNetworkError as exc:
            raise ClickHouseConnectionError(
                f"Cannot connect to ClickHouse at {self._host}:{self._port}: {exc}"
            ) from exc

    def _execute_query(self, query: str, params: dict[str, Any]) -> list[tuple[Any, ...]]:
        client = self._get_client()
        try:
            rows = client.execute(query, params)
        except ClickHouseDriverError as exc:
            raise DashboardQueryError(f"Dashboard query failed: {exc}") from exc
        return cast("list[tuple[Any, ...]]", rows)

    def _repo_metadata_table_exists(self) -> bool:
        rows = self._execute_query("EXISTS TABLE github_analyzer.repo_metadata", {})
        if not rows or not rows[0]:
            return False
        try:
            return int(rows[0][0]) == 1
        except (TypeError, ValueError):
            return True

    async def get_top_repos(
        self,
        *,
        category: str | None,
        days: int,
        limit: int,
    ) -> list[dict[str, object]]:
        params = {"category": category or "", "days": days, "limit": limit}
        query = (
            _TOP_REPOS_QUERY
            if self._repo_metadata_table_exists()
            else (
                _TOP_REPOS_CATEGORY_FALLBACK_QUERY if category else _TOP_REPOS_ALL_FALLBACK_QUERY
            )
        )

        def _run() -> list[dict[str, object]]:
            rows = self._execute_query(query, params)
            repos = [self._parse_repo_metric_row(row) for row in rows]
            if repos:
                return repos
            return self._load_top_repos_from_parquet(days=days, limit=limit, category=category)

        return await asyncio.to_thread(_run)

    async def get_trending(self, *, days: int, limit: int) -> list[dict[str, object]]:
        params = {"days": days, "limit": limit}
        query = _TRENDING_QUERY if self._repo_metadata_table_exists() else _TRENDING_FALLBACK_QUERY

        def _run() -> list[dict[str, object]]:
            rows = self._execute_query(query, params)
            items = [self._parse_repo_metric_row(row) for row in rows]
            for index, item in enumerate(items, start=1):
                item["growth_rank"] = index
            return items

        return await asyncio.to_thread(_run)

    async def get_language_breakdown(
        self,
        *,
        days: int,
        limit: int = 20,
    ) -> list[dict[str, object]]:
        def _run() -> list[dict[str, object]]:
            rows = self._execute_query(_LANGUAGE_BREAKDOWN_QUERY, {"days": days, "limit": limit})
            return [
                {
                    "language": str(row[0]),
                    "star_count": int(row[1]),
                    "repo_count": int(row[2]),
                }
                for row in rows
            ]

        return await asyncio.to_thread(_run)

    async def get_topic_breakdown(self, *, days: int, limit: int = 20) -> list[dict[str, object]]:
        def _run() -> list[dict[str, object]]:
            rows = self._execute_query(_TOPIC_BREAKDOWN_QUERY, {"days": days, "limit": limit})
            return [
                {"topic": str(row[0]), "star_count": int(row[1]), "repo_count": int(row[2])}
                for row in rows
            ]

        return await asyncio.to_thread(_run)

    async def get_repo_timeseries(
        self,
        *,
        repo_name: str,
        days: int,
    ) -> list[dict[str, object]]:
        def _run() -> list[dict[str, object]]:
            rows = self._execute_query(
                _REPO_TIMESERIES_QUERY,
                {"repo_name": repo_name, "days": days},
            )
            return [
                {
                    "event_date": _coerce_date(row[0]),
                    "star_count": int(row[1]),
                    "total_events": int(row[2]),
                }
                for row in rows
            ]

        return await asyncio.to_thread(_run)

    async def get_category_summary(
        self,
        *,
        days: int,
        limit: int = 20,
    ) -> list[dict[str, object]]:
        query = (
            _CATEGORY_SUMMARY_QUERY
            if self._repo_metadata_table_exists()
            else (_CATEGORY_SUMMARY_FALLBACK_QUERY)
        )

        def _run() -> list[dict[str, object]]:
            rows = self._execute_query(query, {"days": days, "limit": limit})
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

    async def get_shock_movers(
        self,
        *,
        days: int,
        absolute_limit: int,
        percentage_limit: int,
        min_baseline_stars: int,
    ) -> dict[str, object]:
        query = (
            _SHOCK_MOVERS_QUERY
            if self._repo_metadata_table_exists()
            else _SHOCK_MOVERS_FALLBACK_QUERY
        )

        def _run() -> dict[str, object]:
            rows = self._execute_query(
                query,
                {
                    "days": days,
                    "days_twice": days * 2,
                },
            )
            if not rows and query != _SHOCK_MOVERS_FALLBACK_QUERY:
                rows = self._execute_query(
                    _SHOCK_MOVERS_FALLBACK_QUERY,
                    {
                        "days": days,
                        "days_twice": days * 2,
                    },
                )
            items = [self._parse_shock_mover_row(row) for row in rows]
            absolute = sorted(
                items,
                key=lambda item: (
                    _coerce_int(item["star_count_in_window"]),
                    _coerce_int(item["stargazers_count"]),
                ),
                reverse=True,
            )[:absolute_limit]
            percentage = sorted(
                [
                    item
                    for item in items
                    if _coerce_int(item["stargazers_count"]) >= min_baseline_stars
                ],
                key=lambda item: (
                    _coerce_float(item["weekly_percent_gain"]),
                    _coerce_int(item["star_count_in_window"]),
                ),
                reverse=True,
            )[:percentage_limit]

            for index, item in enumerate(absolute, start=1):
                item["rank"] = index
            for index, item in enumerate(percentage, start=1):
                item["rank"] = index

            return {
                "window_days": days,
                "absolute_movers": absolute,
                "percentage_movers": percentage,
            }

        return await asyncio.to_thread(_run)

    async def get_topic_rotation(self, *, days: int, limit: int) -> list[dict[str, object]]:
        def _run() -> list[dict[str, object]]:
            rows = self._execute_query(
                _TOPIC_ROTATION_QUERY,
                {"days": days, "days_twice": days * 2, "limit": limit},
            )
            result: list[dict[str, object]] = []
            for index, row in enumerate(rows, start=1):
                current = int(row[1])
                previous = int(row[2])
                result.append(
                    {
                        "topic": str(row[0]),
                        "current_star_count": current,
                        "previous_star_count": previous,
                        "star_delta": current - previous,
                        "repo_count": int(row[3]),
                        "rank": index,
                    }
                )
            return result

        return await asyncio.to_thread(_run)

    def _parse_repo_metric_row(self, row: tuple[Any, ...]) -> dict[str, object]:
        return {
            "repo_id": int(row[0]),
            "repo_full_name": str(row[1]),
            "repo_name": str(row[2]),
            "html_url": str(row[3]),
            "description": str(row[4] or ""),
            "primary_language": str(row[5] or ""),
            "topics": list(row[6]) if row[6] else [],
            "category": str(row[7] or "Other"),
            "stargazers_count": int(row[8] or 0),
            "watchers_count": int(row[9] or 0),
            "forks_count": int(row[10] or 0),
            "open_issues_count": int(row[11] or 0),
            "subscribers_count": int(row[12] or 0),
            "owner_login": str(row[13] or ""),
            "owner_avatar_url": str(row[14] or ""),
            "license_name": str(row[15] or ""),
            "github_created_at": _coerce_datetime(row[16]),
            "github_pushed_at": _coerce_datetime(row[17]),
            "rank": int(row[18] or 0),
            "star_count_in_window": int(row[19] or 0),
            "star_delta": int(row[19] or 0),
        }

    def _parse_shock_mover_row(self, row: tuple[Any, ...]) -> dict[str, object]:
        current = int(row[19] or 0)
        previous = int(row[20] or 0)
        percent_gain = (
            float(current * 100.0)
            if previous <= 0
            else round(((current - previous) / previous) * 100.0, 2)
        )
        ratio = float(current) if previous <= 0 else round(current / previous, 4)
        parsed = self._parse_repo_metric_row(row[:20])
        parsed.update(
            {
                "previous_star_count_in_window": previous,
                "unique_actors_in_window": int(row[21] or 0),
                "weekly_percent_gain": percent_gain,
                "window_over_window_ratio": ratio,
            }
        )
        return parsed

    def _load_top_repos_from_parquet(
        self,
        *,
        days: int,
        limit: int,
        category: str | None,
    ) -> list[dict[str, object]]:
        if category not in {None, "", "Other"}:
            return []

        base_path = Path(self._parquet_base_path)
        if not base_path.exists():
            return []

        cutoff = datetime.now(tz=UTC) - timedelta(days=days)
        repos: dict[str, dict[str, object]] = {}

        for parquet_file in sorted(base_path.rglob("*.parquet")):
            event_type = _extract_event_type(parquet_file)
            if event_type != "WatchEvent":
                continue
            parquet_reader = pq.ParquetFile(str(parquet_file))
            for batch in parquet_reader.iter_batches(batch_size=1000):
                for record in batch.to_pylist():
                    repo_full_name = str(record.get("repo_name") or "").strip().lower()
                    if not repo_full_name:
                        continue
                    created_at = _coerce_datetime(record.get("created_at"))
                    if created_at < cutoff:
                        continue
                    current = repos.setdefault(
                        repo_full_name,
                        {
                            "repo_id": int(record.get("repo_id") or 0),
                            "repo_full_name": repo_full_name,
                            "repo_name": repo_full_name.split("/")[-1],
                            "html_url": f"https://github.com/{repo_full_name}",
                            "description": str(record.get("repo_description") or ""),
                            "primary_language": str(record.get("repo_primary_language") or ""),
                            "topics": _coerce_string_list(record.get("repo_topics")),
                            "category": "Other",
                            "stargazers_count": _coerce_int(
                                record.get("repo_stargazers_count"),
                            ),
                            "watchers_count": _coerce_int(
                                record.get("repo_stargazers_count"),
                            ),
                            "forks_count": 0,
                            "open_issues_count": 0,
                            "subscribers_count": 0,
                            "owner_login": repo_full_name.split("/")[0],
                            "owner_avatar_url": "",
                            "license_name": "",
                            "github_created_at": created_at,
                            "github_pushed_at": created_at,
                            "rank": 0,
                            "star_count_in_window": 0,
                            "star_delta": 0,
                        },
                    )
                    current["description"] = str(
                        record.get("repo_description") or current["description"]
                    )
                    current["primary_language"] = str(
                        record.get("repo_primary_language") or current["primary_language"]
                    )
                    current["topics"] = _coerce_string_list(
                        record.get("repo_topics") or current["topics"]
                    )
                    current["stargazers_count"] = max(
                        _coerce_int(current["stargazers_count"]),
                        _coerce_int(record.get("repo_stargazers_count")),
                    )
                    current["watchers_count"] = _coerce_int(current["stargazers_count"])
                    current["github_pushed_at"] = max(
                        cast("datetime", current["github_pushed_at"]),
                        created_at,
                    )
                    current["star_count_in_window"] = (
                        _coerce_int(current["star_count_in_window"]) + 1
                    )
                    current["star_delta"] = _coerce_int(current["star_count_in_window"])

        ranked = sorted(
            repos.values(),
            key=lambda item: (
                _coerce_int(item["stargazers_count"]),
                _coerce_int(item["star_count_in_window"]),
                cast("datetime", item["github_pushed_at"]),
            ),
            reverse=True,
        )
        return ranked[:limit]


def _extract_event_type(path: Path) -> str:
    for part in path.parts:
        if part.startswith("event_type="):
            return part.split("=", maxsplit=1)[1]
    return ""


def _coerce_int(value: object | None) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return 0
    return 0


def _coerce_float(value: object | None) -> float:
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return 0.0
    return 0.0


def _coerce_string_list(value: object | None) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, tuple):
        return [str(item) for item in value]
    return []


def _coerce_datetime(value: object) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return datetime.now(tz=UTC)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    return datetime.now(tz=UTC)


def _coerce_date(value: object) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if hasattr(value, "isoformat"):
        try:
            return cast("date", value)
        except TypeError:
            return datetime.now(tz=UTC).date()
    return datetime.now(tz=UTC).date()
