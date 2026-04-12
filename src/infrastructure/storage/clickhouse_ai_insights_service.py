"""ClickHouse-backed context retrieval for AI repo insight generation."""

from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime
from typing import Any, cast

from clickhouse_driver import Client
from clickhouse_driver.errors import Error as ClickHouseError
from clickhouse_driver.errors import NetworkError as ClickHouseNetworkError

from university.github.src.application.dtos.ai_market_brief_dto import (
    MarketBreakoutRepoDTO,
    MarketBriefContextDTO,
    MarketCategoryMoverDTO,
    MarketTopicShiftDTO,
)
from university.github.src.application.dtos.ai_repo_brief_dto import (
    RepoBriefActivityDTO,
    RepoBriefContextDTO,
    RepoBriefTimeseriesPointDTO,
)
from university.github.src.application.dtos.repo_metadata_dto import RepoMetadataDTO
from university.github.src.domain.exceptions import (
    AIInsightError,
    ClickHouseConnectionError,
    RepoInsightNotFoundError,
)

_REPO_METADATA_QUERY = """
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
    rank
FROM repo_metadata
FINAL
WHERE repo_full_name = %(repo_name)s
LIMIT 1
"""

_REPO_METADATA_FALLBACK_QUERY = """
SELECT
    any(repo_id) AS repo_id,
    normalized_repo_name AS repo_full_name,
    splitByChar('/', normalized_repo_name)[2] AS repo_name_only,
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
    toInt32(0) AS rank
FROM (
    SELECT
        *,
        lowerUTF8(repo_name) AS normalized_repo_name
    FROM github_analyzer.github_data
    WHERE lowerUTF8(repo_name) = lowerUTF8(%(repo_name)s)
) AS raw
GROUP BY normalized_repo_name
LIMIT 1
"""

_REPO_WINDOW_METRICS_QUERY = """
SELECT
    count() AS total_events,
    uniqExact(actor_login) AS unique_actors,
    max(created_at) AS latest_event_at
FROM github_analyzer.github_data
WHERE lowerUTF8(repo_name) = lowerUTF8(%(repo_name)s)
  AND created_at >= now() - INTERVAL %(days)s DAY
"""

_REPO_ACTIVITY_BREAKDOWN_QUERY = """
SELECT
    event_type,
    count() AS event_count
FROM github_analyzer.github_data
WHERE lowerUTF8(repo_name) = lowerUTF8(%(repo_name)s)
  AND created_at >= now() - INTERVAL %(days)s DAY
GROUP BY event_type
ORDER BY event_count DESC, event_type ASC
LIMIT 5
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

_MARKET_REPO_METRICS_SUBQUERY = """
SELECT
    repo_name,
    countIf(event_type = 'WatchEvent') AS star_count_in_window,
    count() AS total_events_in_window,
    uniqExact(actor_login) AS unique_actors_in_window
FROM github_analyzer.github_data
WHERE created_at >= now() - INTERVAL %(days)s DAY
GROUP BY repo_name
"""

_MARKET_BREAKOUT_REPOS_QUERY = (
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
    rm.github_pushed_at AS github_pushed_at,
    rm.rank AS rank,
    metrics.star_count_in_window AS star_count_in_window,
    metrics.total_events_in_window AS total_events_in_window,
    metrics.unique_actors_in_window AS unique_actors_in_window
FROM repo_metadata AS rm
FINAL
INNER JOIN (
    """
    + _MARKET_REPO_METRICS_SUBQUERY
    + """
) AS metrics
    ON metrics.repo_name = rm.repo_full_name
ORDER BY star_count_in_window DESC, total_events_in_window DESC, rm.stargazers_count DESC
LIMIT %(limit)s
"""
)

_MARKET_BREAKOUT_REPOS_FALLBACK_QUERY = """
SELECT
    any(repo_id) AS repo_id,
    repo_name AS repo_full_name,
    splitByChar('/', repo_name)[2] AS repo_name_only,
    concat('https://github.com/', repo_name) AS html_url,
    any(repo_description) AS description,
    any(repo_primary_language) AS primary_language,
    any(repo_topics) AS topics,
    'Other' AS category,
    max(repo_stargazers_count) AS stargazers_count,
    max(repo_stargazers_count) AS watchers_count,
    toInt64(0) AS forks_count,
    toInt64(0) AS open_issues_count,
    toInt64(0) AS subscribers_count,
    splitByChar('/', repo_name)[1] AS owner_login,
    '' AS owner_avatar_url,
    '' AS license_name,
    min(created_at) AS github_created_at,
    max(created_at) AS github_pushed_at,
    toInt32(0) AS rank,
    countIf(event_type = 'WatchEvent') AS star_count_in_window,
    count() AS total_events_in_window,
    uniqExact(actor_login) AS unique_actors_in_window
FROM github_analyzer.github_data
WHERE created_at >= now() - INTERVAL %(days)s DAY
GROUP BY repo_name
ORDER BY star_count_in_window DESC, total_events_in_window DESC, stargazers_count DESC
LIMIT %(limit)s
"""

_MARKET_CATEGORY_MOVERS_QUERY = (
    """
SELECT
    rm.category AS category,
    count() AS active_repo_count,
    sum(metrics.star_count_in_window) AS total_stars_in_window,
    sum(metrics.total_events_in_window) AS total_events_in_window,
    argMax(rm.repo_full_name, metrics.star_count_in_window) AS leader_repo_name,
    max(metrics.star_count_in_window) AS leader_stars_in_window
FROM repo_metadata AS rm
FINAL
INNER JOIN (
    """
    + _MARKET_REPO_METRICS_SUBQUERY
    + """
) AS metrics
    ON metrics.repo_name = rm.repo_full_name
GROUP BY rm.category
ORDER BY total_stars_in_window DESC, total_events_in_window DESC, active_repo_count DESC
"""
)

_MARKET_CATEGORY_MOVERS_FALLBACK_QUERY = (
    """
SELECT
    'Other' AS category,
    count() AS active_repo_count,
    sum(star_count_in_window) AS total_stars_in_window,
    sum(total_events_in_window) AS total_events_in_window,
    argMax(repo_name, star_count_in_window) AS leader_repo_name,
    max(star_count_in_window) AS leader_stars_in_window
FROM (
    """
    + _MARKET_REPO_METRICS_SUBQUERY
    + """
)
"""
)

_MARKET_TOPIC_SHIFTS_QUERY = """
SELECT
    topic,
    uniqExact(repo_name) AS repo_count,
    countIf(event_type = 'WatchEvent') AS star_count_in_window
FROM github_analyzer.github_data
ARRAY JOIN repo_topics AS topic
WHERE created_at >= now() - INTERVAL %(days)s DAY
  AND topic != ''
GROUP BY topic
ORDER BY star_count_in_window DESC, repo_count DESC, topic ASC
LIMIT %(limit)s
"""


class ClickHouseAIInsightsService:
    """Load one repository context for the AI repo brief workflow."""

    def __init__(
        self,
        *,
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

    def _execute_query(
        self,
        query: str,
        params: dict[str, Any],
    ) -> list[tuple[Any, ...]]:
        client = self._get_client()
        try:
            rows = client.execute(query, params)
        except ClickHouseError as exc:
            raise AIInsightError(f"AI insight query failed: {exc}") from exc
        return cast("list[tuple[Any, ...]]", rows)

    def _repo_metadata_table_exists(self) -> bool:
        rows = self._execute_query("EXISTS TABLE github_analyzer.repo_metadata", {})
        if not rows or not rows[0]:
            return False
        try:
            return int(rows[0][0]) == 1
        except (TypeError, ValueError):
            return True

    async def get_repo_brief_context(
        self,
        *,
        repo_name: str,
        days: int,
    ) -> RepoBriefContextDTO:
        """Return repo metadata plus time-window metrics for the insight use case."""
        params: dict[str, Any] = {"repo_name": repo_name, "days": days}

        def _run() -> RepoBriefContextDTO:
            metadata_query = (
                _REPO_METADATA_QUERY
                if self._repo_metadata_table_exists()
                else _REPO_METADATA_FALLBACK_QUERY
            )
            metadata_rows = self._execute_query(
                metadata_query,
                {"repo_name": repo_name},
            )
            if not metadata_rows:
                metadata_rows = self._execute_query(
                    _REPO_METADATA_FALLBACK_QUERY,
                    {"repo_name": repo_name},
                )
            if not metadata_rows:
                raise RepoInsightNotFoundError(f"Repository not found: {repo_name}")

            repo = _parse_repo_metadata_row(metadata_rows[0])
            metrics_rows = self._execute_query(_REPO_WINDOW_METRICS_QUERY, params)
            activity_rows = self._execute_query(_REPO_ACTIVITY_BREAKDOWN_QUERY, params)
            timeseries_rows = self._execute_query(_REPO_TIMESERIES_QUERY, params)

            total_events = (
                int(metrics_rows[0][0]) if metrics_rows and metrics_rows[0][0] is not None else 0
            )
            unique_actors = (
                int(metrics_rows[0][1]) if metrics_rows and metrics_rows[0][1] is not None else 0
            )
            latest_event_at = (
                _coerce_datetime(metrics_rows[0][2])
                if metrics_rows and metrics_rows[0][2] is not None
                else None
            )
            activity_breakdown = [
                RepoBriefActivityDTO(event_type=str(row[0]), event_count=int(row[1]))
                for row in activity_rows
            ]
            timeseries = [
                RepoBriefTimeseriesPointDTO(
                    event_date=_coerce_date(row[0]),
                    star_count=int(row[1]),
                    total_events=int(row[2]),
                )
                for row in timeseries_rows
            ]
            star_count_in_window = sum(point.star_count for point in timeseries)

            return RepoBriefContextDTO(
                repo=repo,
                window_days=days,
                star_count_in_window=star_count_in_window,
                total_events_in_window=total_events,
                unique_actors_in_window=unique_actors,
                latest_event_at=latest_event_at,
                activity_breakdown=activity_breakdown,
                timeseries=timeseries,
            )

        return await asyncio.to_thread(_run)

    async def get_market_brief_context(
        self,
        *,
        days: int,
        breakout_limit: int,
        category_limit: int,
        topic_limit: int,
    ) -> MarketBriefContextDTO:
        """Return aggregated market context for the AI market brief workflow."""
        params: dict[str, Any] = {"days": days}

        def _run() -> MarketBriefContextDTO:
            has_metadata = self._repo_metadata_table_exists()
            breakout_query = (
                _MARKET_BREAKOUT_REPOS_QUERY
                if has_metadata
                else _MARKET_BREAKOUT_REPOS_FALLBACK_QUERY
            )
            category_query = (
                _MARKET_CATEGORY_MOVERS_QUERY
                if has_metadata
                else _MARKET_CATEGORY_MOVERS_FALLBACK_QUERY
            )

            breakout_rows = self._execute_query(
                breakout_query,
                {**params, "limit": breakout_limit},
            )
            if not breakout_rows and breakout_query != _MARKET_BREAKOUT_REPOS_FALLBACK_QUERY:
                breakout_rows = self._execute_query(
                    _MARKET_BREAKOUT_REPOS_FALLBACK_QUERY,
                    {**params, "limit": breakout_limit},
                )
            category_rows = self._execute_query(category_query, params)
            topic_rows = self._execute_query(
                _MARKET_TOPIC_SHIFTS_QUERY,
                {**params, "limit": topic_limit},
            )

            breakouts = [_parse_market_breakout_row(row) for row in breakout_rows][:breakout_limit]
            categories = _parse_market_category_rows(category_rows)[:category_limit]
            topics = [
                MarketTopicShiftDTO(
                    topic=str(row[0]),
                    repo_count=int(row[1]),
                    star_count_in_window=int(row[2]),
                )
                for row in topic_rows
            ]
            return MarketBriefContextDTO(
                window_days=days,
                breakout_repos=breakouts,
                category_movers=categories,
                topic_shifts=topics,
            )

        return await asyncio.to_thread(_run)


def _parse_repo_metadata_row(row: tuple[Any, ...]) -> RepoMetadataDTO:
    topics_raw = row[6]
    return RepoMetadataDTO(
        repo_id=int(row[0]),
        repo_full_name=str(row[1]),
        repo_name=str(row[2]),
        html_url=str(row[3]),
        description=str(row[4]),
        primary_language=str(row[5]),
        topics=list(topics_raw) if topics_raw else [],
        category=str(row[7]),
        stargazers_count=int(row[8]),
        watchers_count=int(row[9]),
        forks_count=int(row[10]),
        open_issues_count=int(row[11]),
        subscribers_count=int(row[12]),
        owner_login=str(row[13]),
        owner_avatar_url=str(row[14]),
        license_name=str(row[15]),
        github_created_at=_coerce_datetime(row[16]),
        github_pushed_at=_coerce_datetime(row[17]),
        rank=int(row[18]),
    )


def _parse_market_breakout_row(row: tuple[Any, ...]) -> MarketBreakoutRepoDTO:
    repo = _parse_repo_metadata_row(row[:19])
    momentum_base = max(repo.stargazers_count, 1)
    return MarketBreakoutRepoDTO(
        repo=repo,
        star_count_in_window=int(row[19]),
        total_events_in_window=int(row[20]),
        unique_actors_in_window=int(row[21]),
        momentum_score=round(int(row[19]) / momentum_base, 4),
    )


def _parse_market_category_rows(
    rows: list[tuple[Any, ...]],
) -> list[MarketCategoryMoverDTO]:
    total_stars = sum(int(row[2]) for row in rows) or 1
    return [
        MarketCategoryMoverDTO(
            category=str(row[0]),
            active_repo_count=int(row[1]),
            total_stars_in_window=int(row[2]),
            total_events_in_window=int(row[3]),
            leader_repo_name=str(row[4]),
            leader_stars_in_window=int(row[5]),
            share_of_window_stars=round(int(row[2]) / total_stars, 4),
        )
        for row in rows
    ]


def _coerce_datetime(value: object) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    return datetime.now(tz=UTC)


def _coerce_date(value: object) -> date:
    if isinstance(value, date):
        return value
    return datetime.now(tz=UTC).date()
