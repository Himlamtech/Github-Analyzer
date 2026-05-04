"""ClickHouseDashboardService — analytical queries powering the dashboard.

Single-responsibility service for the 6 dashboard endpoints.
Kept separate from ``ClickHouseRepoMetadataRepository`` to honour SRP:
the repository handles CRUD for RepoMetadata, this service handles
multi-table analytical joins.

Uses ``clickhouse-driver`` (sync) wrapped in ``asyncio.to_thread``.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
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

# ── SQL Queries ───────────────────────────────────────────────────────────────

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
    any(repo_stargazers_count) AS stargazers_count,
    any(repo_stargazers_count) AS watchers_count,
    toInt64(0) AS forks_count,
    toInt64(0) AS open_issues_count,
    toInt64(0) AS subscribers_count,
    splitByChar('/', normalized_repo_name)[1] AS owner_login,
    '' AS owner_avatar_url,
    '' AS license_name,
    now() AS github_created_at,
    max(created_at) AS github_pushed_at,
    toInt32(0) AS rank,
    countIf(event_type = 'WatchEvent') AS star_count_in_window
FROM (
    SELECT
        *,
        lowerUTF8(repo_name) AS normalized_repo_name
    FROM github_analyzer.github_data
    WHERE created_at >= now() - INTERVAL %(days)s DAY
) AS raw
GROUP BY normalized_repo_name
ORDER BY star_count_in_window DESC, any(repo_stargazers_count) DESC
LIMIT %(limit)s
"""

_TOP_STARRED_REPOS_ALL_FALLBACK_QUERY = """
SELECT
    any(repo_id) AS repo_id,
    normalized_repo_name AS repo_full_name,
    splitByChar('/', normalized_repo_name)[2] AS repo_name,
    concat('https://github.com/', normalized_repo_name) AS html_url,
    any(repo_description) AS description,
    any(repo_primary_language) AS primary_language,
    any(repo_topics) AS topics,
    'Other' AS category,
    any(repo_stargazers_count) AS stargazers_count,
    any(repo_stargazers_count) AS watchers_count,
    toInt64(0) AS forks_count,
    toInt64(0) AS open_issues_count,
    toInt64(0) AS subscribers_count,
    splitByChar('/', normalized_repo_name)[1] AS owner_login,
    '' AS owner_avatar_url,
    '' AS license_name,
    min(created_at) AS github_created_at,
    max(created_at) AS github_pushed_at,
    toInt32(0) AS rank,
    toInt64(0) AS star_count_in_window
FROM (
    SELECT
        *,
        lowerUTF8(repo_name) AS normalized_repo_name
    FROM github_analyzer.github_data
) AS raw
GROUP BY normalized_repo_name
ORDER BY max(repo_stargazers_count) DESC, normalized_repo_name ASC
LIMIT %(limit)s
"""

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
    any(repo_stargazers_count) AS stargazers_count,
    any(repo_stargazers_count) AS watchers_count,
    toInt64(0) AS forks_count,
    toInt64(0) AS open_issues_count,
    toInt64(0) AS subscribers_count,
    splitByChar('/', normalized_repo_name)[1] AS owner_login,
    '' AS owner_avatar_url,
    '' AS license_name,
    now() AS github_created_at,
    max(created_at) AS github_pushed_at,
    toInt32(0) AS rank,
    countIf(event_type = 'WatchEvent') AS star_count_in_window
FROM (
    SELECT
        *,
        lowerUTF8(repo_name) AS normalized_repo_name
    FROM github_analyzer.github_data
    WHERE created_at >= now() - INTERVAL %(days)s DAY
) AS raw
GROUP BY normalized_repo_name
HAVING %(category)s = 'Other'
ORDER BY star_count_in_window DESC, any(repo_stargazers_count) DESC
LIMIT %(limit)s
"""

_TOP_STARRED_REPOS_CATEGORY_FALLBACK_QUERY = """
SELECT
    any(repo_id) AS repo_id,
    normalized_repo_name AS repo_full_name,
    splitByChar('/', normalized_repo_name)[2] AS repo_name,
    concat('https://github.com/', normalized_repo_name) AS html_url,
    any(repo_description) AS description,
    any(repo_primary_language) AS primary_language,
    any(repo_topics) AS topics,
    'Other' AS category,
    any(repo_stargazers_count) AS stargazers_count,
    any(repo_stargazers_count) AS watchers_count,
    toInt64(0) AS forks_count,
    toInt64(0) AS open_issues_count,
    toInt64(0) AS subscribers_count,
    splitByChar('/', normalized_repo_name)[1] AS owner_login,
    '' AS owner_avatar_url,
    '' AS license_name,
    min(created_at) AS github_created_at,
    max(created_at) AS github_pushed_at,
    toInt32(0) AS rank,
    toInt64(0) AS star_count_in_window
FROM (
    SELECT
        *,
        lowerUTF8(repo_name) AS normalized_repo_name
    FROM github_analyzer.github_data
) AS raw
GROUP BY normalized_repo_name
HAVING %(category)s = 'Other'
ORDER BY max(repo_stargazers_count) DESC, normalized_repo_name ASC
LIMIT %(limit)s
"""

# Trending: ranked by stars added since the current GMT+7 week started.
_TRENDING_QUERY = """
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
    SELECT
        repo_name,
        countIf(event_type = 'WatchEvent') AS star_count_in_window,
        max(created_at) AS latest_event_at
    FROM github_data
    WHERE created_at >= %(week_start)s
      AND created_at < %(week_end)s
    GROUP BY repo_name
) AS metrics
    ON metrics.repo_name = rm.repo_full_name
ORDER BY star_count_in_window DESC, rm.stargazers_count DESC
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
    any(repo_stargazers_count) AS stargazers_count,
    any(repo_stargazers_count) AS watchers_count,
    toInt64(0) AS forks_count,
    toInt64(0) AS open_issues_count,
    toInt64(0) AS subscribers_count,
    splitByChar('/', normalized_repo_name)[1] AS owner_login,
    '' AS owner_avatar_url,
    '' AS license_name,
    now() AS github_created_at,
    max(created_at) AS github_pushed_at,
    toInt32(0) AS rank,
    countIf(event_type = 'WatchEvent') AS star_count_in_window
FROM (
    SELECT
        *,
        lowerUTF8(repo_name) AS normalized_repo_name
    FROM github_analyzer.github_data
    WHERE created_at >= %(week_start)s
      AND created_at < %(week_end)s
) AS raw
GROUP BY normalized_repo_name
ORDER BY star_count_in_window DESC, any(repo_stargazers_count) DESC
LIMIT %(limit)s
"""
_TOPIC_BREAKDOWN_QUERY = """
SELECT
    topic,
    countIf(gd.event_type = 'WatchEvent') AS event_count,
    COUNT(DISTINCT gd.repo_name)     AS repo_count
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
    gd.repo_primary_language         AS language,
    countIf(gd.event_type = 'WatchEvent') AS event_count,
    COUNT(DISTINCT gd.repo_name)     AS repo_count
FROM github_analyzer.github_data AS gd
WHERE gd.created_at >= now() - INTERVAL %(days)s DAY
  AND gd.repo_primary_language != ''
GROUP BY gd.repo_primary_language
HAVING event_count > 0
ORDER BY event_count DESC
LIMIT 20
"""

# Drives the "Star Growth" chart. Reads directly from github_data so data
# is visible even before repo_star_counts is populated by the batch job.
_REPO_TIMESERIES_QUERY = """
SELECT
    toDate(ge.created_at)                         AS event_date,
    countIf(ge.event_type = 'WatchEvent')          AS star_count,
    count()                                        AS total_events
FROM github_analyzer.github_data AS ge
WHERE
    ge.repo_name   = %(repo_name)s
    AND ge.created_at >= now() - INTERVAL %(days)s DAY
GROUP BY event_date
ORDER BY event_date ASC
"""

# Groups all event-observed repos by their metadata category.
# When repo_metadata is sparse, seen repos fall into 'Other'.
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

_CATEGORY_SUMMARY_FALLBACK_QUERY = """
SELECT
    'Other' AS category,
    COUNT(DISTINCT ge.repo_name) AS repo_count,
    SUM(ge.repo_stargazers_count) AS total_stars,
    argMax(ge.repo_name, ge.repo_stargazers_count) AS top_repo_name,
    MAX(ge.repo_stargazers_count) AS top_repo_stars,
    countIf(ge.event_type = 'WatchEvent') AS weekly_star_delta
FROM github_analyzer.github_data AS ge
WHERE ge.created_at >= now() - INTERVAL 7 DAY
GROUP BY category
ORDER BY repo_count DESC
"""

_CATEGORY_SUMMARY_SOURCE_FALLBACK_QUERY = """
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
    countIf(event_type = 'WatchEvent' AND created_at >= now() - INTERVAL 7 DAY)
        AS star_count_in_window
FROM (
    SELECT
        *,
        lowerUTF8(repo_name) AS normalized_repo_name
    FROM github_analyzer.github_data
) AS raw
GROUP BY normalized_repo_name
HAVING star_count_in_window > 0
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

_SHOCK_MOVERS_ABSOLUTE_FALLBACK_QUERY = """
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
    countIf(
        event_type = 'WatchEvent'
        AND created_at >= now() - INTERVAL %(days)s DAY
    ) AS star_count_in_window,
    countIf(
        event_type = 'WatchEvent'
        AND created_at < now() - INTERVAL %(days)s DAY
        AND created_at >= now() - INTERVAL %(days_twice)s DAY
    ) AS previous_star_count_in_window,
    uniqExactIf(
        actor_login,
        created_at >= now() - INTERVAL %(days)s DAY
    ) AS unique_actors_in_window,
    round(
        (
            countIf(
                event_type = 'WatchEvent'
                AND created_at >= now() - INTERVAL %(days)s DAY
            )
            / greatest(
                max(repo_stargazers_count)
                - countIf(
                    event_type = 'WatchEvent'
                    AND created_at >= now() - INTERVAL %(days)s DAY
                ),
                1
            )
        ) * 100,
        2
    ) AS weekly_percent_gain,
    round(
        countIf(
            event_type = 'WatchEvent'
            AND created_at >= now() - INTERVAL %(days)s DAY
        )
        / greatest(
            countIf(
                event_type = 'WatchEvent'
                AND created_at < now() - INTERVAL %(days)s DAY
                AND created_at >= now() - INTERVAL %(days_twice)s DAY
            ),
            1
        ),
        4
    ) AS window_over_window_ratio
FROM (
    SELECT
        *,
        lowerUTF8(repo_name) AS normalized_repo_name
    FROM github_analyzer.github_data
    WHERE created_at >= now() - INTERVAL %(days_twice)s DAY
) AS raw
GROUP BY normalized_repo_name
HAVING star_count_in_window > 0
ORDER BY
    star_count_in_window DESC,
    unique_actors_in_window DESC,
    stargazers_count DESC
LIMIT %(limit)s
"""

_SHOCK_MOVERS_PERCENTAGE_FALLBACK_QUERY = (
    """
SELECT *
FROM (
    """
    + _SHOCK_MOVERS_ABSOLUTE_FALLBACK_QUERY.replace(
        "LIMIT %(limit)s",
        "",
    )
    + """
) AS movers
WHERE greatest(stargazers_count - star_count_in_window, 0) >= %(min_baseline_stars)s
ORDER BY
    weekly_percent_gain DESC,
    star_count_in_window DESC,
    unique_actors_in_window DESC
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

_PARQUET_TOP_REPOS_QUERY = """
WITH repo_metrics AS (
    SELECT
        repo_id,
        repo_name AS repo_full_name,
        split_part(repo_name, '/', 2) AS repo_name_only,
        max(repo_description) AS description,
        max(repo_primary_language) AS primary_language,
        list_distinct(
            list_filter(flatten(list(repo_topics)), x -> x IS NOT NULL AND x != '')
        ) AS topics,
        max(repo_stargazers_count) AS stargazers_count,
        split_part(repo_name, '/', 1) AS owner_login,
        min(created_at) AS github_created_at,
        max(created_at) AS github_pushed_at,
        count() FILTER (WHERE event_type = 'WatchEvent') AS star_count_in_window
    FROM read_parquet(?, hive_partitioning = true, union_by_name = true)
    WHERE event_date >= CAST(? AS DATE)
    GROUP BY repo_id, repo_name
)
SELECT
    repo_id,
    repo_full_name,
    repo_name_only,
    'https://github.com/' || repo_full_name AS html_url,
    description,
    primary_language,
    topics,
    'Other' AS category,
    stargazers_count,
    stargazers_count AS watchers_count,
    0 AS forks_count,
    0 AS open_issues_count,
    0 AS subscribers_count,
    owner_login,
    '' AS owner_avatar_url,
    '' AS license_name,
    github_created_at,
    github_pushed_at,
    0 AS rank,
    star_count_in_window
FROM repo_metrics
WHERE (? IS NULL OR ? = 'Other')
ORDER BY star_count_in_window DESC, stargazers_count DESC
LIMIT ?
"""

_PARQUET_TOP_STARRED_REPOS_QUERY = """
WITH repo_metrics AS (
    SELECT
        repo_id,
        repo_name AS repo_full_name,
        split_part(repo_name, '/', 2) AS repo_name_only,
        max(repo_description) AS description,
        max(repo_primary_language) AS primary_language,
        list_distinct(
            list_filter(flatten(list(repo_topics)), x -> x IS NOT NULL AND x != '')
        ) AS topics,
        max(repo_stargazers_count) AS stargazers_count,
        split_part(repo_name, '/', 1) AS owner_login,
        min(created_at) AS github_created_at,
        max(created_at) AS github_pushed_at,
        0 AS star_count_in_window
    FROM read_parquet(?, hive_partitioning = true, union_by_name = true)
    GROUP BY repo_id, repo_name
)
SELECT
    repo_id,
    repo_full_name,
    repo_name_only,
    'https://github.com/' || repo_full_name AS html_url,
    description,
    primary_language,
    topics,
    'Other' AS category,
    stargazers_count,
    stargazers_count AS watchers_count,
    0 AS forks_count,
    0 AS open_issues_count,
    0 AS subscribers_count,
    owner_login,
    '' AS owner_avatar_url,
    '' AS license_name,
    github_created_at,
    github_pushed_at,
    0 AS rank,
    star_count_in_window
FROM repo_metrics
WHERE (? IS NULL OR ? = 'Other')
ORDER BY stargazers_count DESC, repo_full_name ASC
LIMIT ?
"""

_PARQUET_TRENDING_QUERY = """
WITH repo_metrics AS (
    SELECT
        repo_id,
        repo_name AS repo_full_name,
        split_part(repo_name, '/', 2) AS repo_name_only,
        max(repo_description) AS description,
        max(repo_primary_language) AS primary_language,
        list_distinct(
            list_filter(flatten(list(repo_topics)), x -> x IS NOT NULL AND x != '')
        ) AS topics,
        max(repo_stargazers_count) AS stargazers_count,
        split_part(repo_name, '/', 1) AS owner_login,
        min(created_at) AS github_created_at,
        max(created_at) AS github_pushed_at,
        count(*) FILTER (WHERE event_type = 'WatchEvent') AS star_count_in_window
    FROM read_parquet(?, hive_partitioning = true, union_by_name = true)
    WHERE event_date >= CAST(? AS DATE)
      AND created_at >= ?
      AND created_at < ?
    GROUP BY repo_id, repo_name
)
SELECT
    repo_id,
    repo_full_name,
    repo_name_only,
    'https://github.com/' || repo_full_name AS html_url,
    description,
    primary_language,
    topics,
    'Other' AS category,
    stargazers_count,
    stargazers_count AS watchers_count,
    0 AS forks_count,
    0 AS open_issues_count,
    0 AS subscribers_count,
    owner_login,
    '' AS owner_avatar_url,
    '' AS license_name,
    github_created_at,
    github_pushed_at,
    0 AS rank,
    star_count_in_window
FROM repo_metrics
WHERE star_count_in_window > 0
ORDER BY star_count_in_window DESC, stargazers_count DESC
LIMIT ?
"""

_PARQUET_TOPIC_BREAKDOWN_QUERY = """
SELECT
    topic,
    count(*) FILTER (WHERE event_type = 'WatchEvent') AS event_count,
    count(DISTINCT repo_name) AS repo_count
FROM (
    SELECT
        repo_name,
        event_type,
        unnest(repo_topics) AS topic
    FROM read_parquet(?, hive_partitioning = true, union_by_name = true)
    WHERE event_date >= CAST(? AS DATE)
)
WHERE topic IS NOT NULL AND topic != ''
GROUP BY topic
HAVING event_count > 0
ORDER BY event_count DESC
LIMIT 30
"""

_PARQUET_LANGUAGE_BREAKDOWN_QUERY = """
SELECT
    repo_primary_language AS language,
    count(*) FILTER (WHERE event_type = 'WatchEvent') AS event_count,
    count(DISTINCT repo_name) AS repo_count
FROM read_parquet(?, hive_partitioning = true, union_by_name = true)
WHERE event_date >= CAST(? AS DATE)
  AND repo_primary_language IS NOT NULL
  AND repo_primary_language != ''
GROUP BY repo_primary_language
HAVING event_count > 0
ORDER BY event_count DESC
LIMIT 20
"""

_PARQUET_REPO_TIMESERIES_QUERY = """
SELECT
    CAST(event_date AS DATE) AS event_date,
    count(*) FILTER (WHERE event_type = 'WatchEvent') AS star_count,
    count(*) AS total_events
FROM read_parquet(?, hive_partitioning = true, union_by_name = true)
WHERE event_date >= CAST(? AS DATE)
  AND repo_name = ?
GROUP BY event_date
ORDER BY event_date ASC
"""

_PARQUET_CATEGORY_SUMMARY_QUERY = """
WITH repo_metrics AS (
    SELECT
        repo_name,
        max(repo_stargazers_count) AS stargazers_count,
        count(*) FILTER (WHERE event_date >= CAST(? AS DATE)
                         AND event_type = 'WatchEvent') AS weekly_star_delta
    FROM read_parquet(?, hive_partitioning = true, union_by_name = true)
    GROUP BY repo_name
)
SELECT
    'Other' AS category,
    count(*) AS repo_count,
    coalesce(sum(stargazers_count), 0) AS total_stars,
    arg_max(repo_name, stargazers_count) AS top_repo_name,
    coalesce(max(stargazers_count), 0) AS top_repo_stars,
    coalesce(sum(weekly_star_delta), 0) AS weekly_star_delta
FROM repo_metrics
"""


class ClickHouseDashboardService:
    """Executes the six analytical queries powering the dashboard UI.

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
        parquet_base_path: str = "./data/raw",
    ) -> None:
        self._host = host
        self._port = port
        self._user = user
        self._password = password
        self._database = database
        self._parquet_base_path = parquet_base_path.rstrip("/")
        self._classifier = CategoryClassifier()
        self._has_categorized_metadata_cache: bool | None = None

    def _get_client(self) -> Client:
        """Create a ClickHouse client connection.

        Raises:
            ClickHouseConnectionError: If connection fails.
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

    def _execute_query(
        self,
        query: str,
        params: dict[str, Any] | None = None,
    ) -> list[tuple[Any, ...]]:
        """Execute a SELECT query and return raw rows.

        Args:
            query:  SQL query string.
            params: Optional parameter dict for parameterised queries.

        Returns:
            List of row tuples from ClickHouse.

        Raises:
            DashboardQueryError: On ClickHouse query failure.
        """
        client = self._get_client()
        try:
            rows = client.execute(query, params or {})
            return cast("list[tuple[Any, ...]]", rows)
        except ClickHouseError as exc:
            raise DashboardQueryError(f"Dashboard query failed: {exc}") from exc

    @staticmethod
    def _should_fallback_to_raw_events(exc: DashboardQueryError) -> bool:
        message = str(exc)
        return "repo_metadata" in message and (
            "Unknown table expression identifier" in message or "UNKNOWN_TABLE" in message
        )

    def _repo_metadata_table_exists(self) -> bool:
        rows = self._execute_query(
            "EXISTS TABLE github_analyzer.repo_metadata",
        )
        if not rows or not rows[0]:
            return False
        try:
            return int(rows[0][0]) == 1
        except (TypeError, ValueError):
            # Test doubles may stub .execute() with business rows for all queries.
            return True

    def _has_categorized_repo_metadata(self) -> bool:
        if self._has_categorized_metadata_cache is not None:
            return self._has_categorized_metadata_cache
        if not self._repo_metadata_table_exists():
            self._has_categorized_metadata_cache = False
            return False

        try:
            rows = self._execute_query(
                """
SELECT countIf(category != 'Other')
FROM github_analyzer.repo_metadata
FINAL
""",
            )
        except DashboardQueryError:
            self._has_categorized_metadata_cache = False
            return False
        try:
            self._has_categorized_metadata_cache = int(rows[0][0]) > 0
        except (IndexError, TypeError, ValueError):
            self._has_categorized_metadata_cache = True
        return self._has_categorized_metadata_cache

    def _parquet_glob_path(self) -> str:
        return f"{self._parquet_base_path}/event_date=*/event_type=*/*.parquet"

    @staticmethod
    def _cutoff_date(days: int) -> str:
        cutoff = datetime.now(tz=UTC).date() - timedelta(days=days)
        return cutoff.isoformat()

    @staticmethod
    def _current_gmt7_week_bounds(
        now: datetime | None = None,
    ) -> tuple[datetime, datetime]:
        """Return the current GMT+7 week window as UTC datetimes."""
        current_utc = now or datetime.now(tz=UTC)
        local_now = current_utc.astimezone(_GMT7)
        week_start_local = datetime.combine(
            (local_now.date() - timedelta(days=local_now.weekday())),
            datetime.min.time(),
            tzinfo=_GMT7,
        )
        week_start_utc = week_start_local.astimezone(UTC)
        return week_start_utc, current_utc

    def _parquet_data_exists(self) -> bool:
        return Path(self._parquet_base_path).exists() and any(
            Path(self._parquet_base_path).glob("event_date=*")
        )

    def _parquet_query_paths(self, days: int) -> list[str]:
        """Return only the partition globs that intersect the requested window."""
        base_path = Path(self._parquet_base_path)
        if not base_path.exists():
            return []

        cutoff = self._cutoff_date(days)
        partition_dates = sorted(
            path.name.split("=", maxsplit=1)[1]
            for path in base_path.glob("event_date=*")
            if path.is_dir() and "=" in path.name
        )
        return [
            f"{self._parquet_base_path}/event_date={partition_date}/event_type=*/*.parquet"
            for partition_date in partition_dates
            if partition_date >= cutoff
        ]

    def _parquet_all_query_paths(self) -> list[str]:
        """Return all available parquet partitions."""
        base_path = Path(self._parquet_base_path)
        if not base_path.exists():
            return []
        partition_dates = sorted(
            path.name.split("=", maxsplit=1)[1]
            for path in base_path.glob("event_date=*")
            if path.is_dir() and "=" in path.name
        )
        return [
            f"{self._parquet_base_path}/event_date={partition_date}/event_type=*/*.parquet"
            for partition_date in partition_dates
        ]

    def _execute_parquet_query(
        self,
        query: str,
        params: list[Any],
    ) -> list[tuple[Any, ...]]:
        try:
            import duckdb
        except ModuleNotFoundError as exc:
            raise DashboardQueryError(
                "Dashboard parquet fallback unavailable: duckdb is not installed"
            ) from exc

        try:
            conn = duckdb.connect(database=":memory:", read_only=False)
            try:
                rows = conn.execute(query, params).fetchall()
            finally:
                conn.close()
            return rows
        except duckdb.Error as exc:
            raise DashboardQueryError(f"Dashboard parquet query failed: {exc}") from exc

    @staticmethod
    def _parse_repo_row(row: tuple[Any, ...]) -> dict[str, Any]:
        """Map a SELECT row (19 repo fields + star_count_in_window) to dict."""
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
        exclude_uncategorized: bool = False,
    ) -> list[dict[str, Any]]:
        if category is None and exclude_uncategorized:
            filtered_items = [
                item for item in items if item["category"] != RepoCategory.OTHER.value
            ]
            if filtered_items:
                return filtered_items[:limit]
        if category is None:
            return items[:limit]
        return [item for item in items if item["category"] == category][:limit]

    async def get_top_repos(
        self,
        category: str | None,
        days: int,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Top repos by star count in window, optionally filtered by category.

        Args:
            category: Optional category filter (e.g., ``"LLM"``). ``None`` means all.
            days:     Look-back window in days.
            limit:    Maximum rows to return.

        Returns:
            List of dicts: repo fields + star_count_in_window.
        """
        has_categorized_metadata = self._has_categorized_repo_metadata()
        if category and has_categorized_metadata:
            params: dict[str, Any] = {
                "category": category,
                "days": days,
                "limit": limit,
            }
            query = _TOP_REPOS_CATEGORY_QUERY
        else:
            params = {
                "days": days,
                "limit": limit if has_categorized_metadata else max(limit * 8, 40),
            }
            query = (
                _TOP_REPOS_ALL_QUERY if has_categorized_metadata else _TOP_REPOS_ALL_FALLBACK_QUERY
            )

        def _run() -> list[dict[str, Any]]:
            fallback_query = (
                _TOP_REPOS_CATEGORY_FALLBACK_QUERY
                if category and has_categorized_metadata
                else _TOP_REPOS_ALL_FALLBACK_QUERY
            )
            try:
                rows = self._execute_query(query, params)
            except DashboardQueryError as exc:
                if not self._should_fallback_to_raw_events(exc):
                    raise
                rows = self._execute_query(fallback_query, params)
            if not rows:
                rows = self._execute_query(fallback_query, params)
            parquet_paths = self._parquet_query_paths(days)
            if not rows and parquet_paths:
                rows = self._execute_parquet_query(
                    _PARQUET_TOP_REPOS_QUERY,
                    [
                        parquet_paths,
                        self._cutoff_date(days),
                        category,
                        category,
                        limit,
                    ],
                )
            items = [self._parse_repo_row(r) for r in rows]
            return self._apply_category_filter(
                items,
                category=category,
                limit=limit,
                exclude_uncategorized=not has_categorized_metadata,
            )

        return await asyncio.to_thread(_run)

    async def get_top_starred_repos(
        self,
        category: str | None,
        limit: int,
        days: int = 7,
    ) -> list[dict[str, Any]]:
        """Top repos by current all-time star count, optionally filtered by category."""
        has_categorized_metadata = self._has_categorized_repo_metadata()
        if category and has_categorized_metadata:
            params: dict[str, Any] = {
                "category": category,
                "days": days,
                "limit": limit,
            }
            query = _TOP_STARRED_REPOS_CATEGORY_QUERY
        else:
            params = {
                "days": days,
                "limit": limit if has_categorized_metadata else max(limit * 8, 40),
            }
            query = (
                _TOP_STARRED_REPOS_ALL_QUERY
                if has_categorized_metadata
                else _TOP_STARRED_REPOS_ALL_FALLBACK_QUERY
            )

        def _run() -> list[dict[str, Any]]:
            fallback_query = (
                _TOP_STARRED_REPOS_CATEGORY_FALLBACK_QUERY
                if category and has_categorized_metadata
                else _TOP_STARRED_REPOS_ALL_FALLBACK_QUERY
            )
            try:
                rows = self._execute_query(query, params)
            except DashboardQueryError as exc:
                if not self._should_fallback_to_raw_events(exc):
                    raise
                rows = self._execute_query(fallback_query, params)
            if not rows:
                rows = self._execute_query(fallback_query, params)
            parquet_paths = self._parquet_all_query_paths()
            if not rows and parquet_paths:
                rows = self._execute_parquet_query(
                    _PARQUET_TOP_STARRED_REPOS_QUERY,
                    [
                        parquet_paths,
                        category,
                        category,
                        limit,
                    ],
                )
            items = [self._parse_repo_row(r) for r in rows]
            return self._apply_category_filter(
                items,
                category=category,
                limit=limit,
                exclude_uncategorized=not has_categorized_metadata,
            )

        return await asyncio.to_thread(_run)

    async def get_trending(self, days: int, limit: int) -> list[dict[str, Any]]:
        """Trending repos by stars added in the current GMT+7 week.

        Args:
            days:  Retained for API compatibility; current-week ranking ignores it.
            limit: Maximum rows to return.

        Returns:
            List of dicts: repo fields + star_count_in_window, with growth_rank added.
        """
        has_categorized_metadata = self._has_categorized_repo_metadata()
        week_start, week_end = self._current_gmt7_week_bounds()
        params: dict[str, Any] = {
            "week_start": week_start,
            "week_end": week_end,
            "limit": limit if has_categorized_metadata else max(limit * 8, 40),
        }
        query = _TRENDING_QUERY if has_categorized_metadata else _TRENDING_FALLBACK_QUERY

        def _run() -> list[dict[str, Any]]:
            try:
                rows = self._execute_query(query, params)
            except DashboardQueryError as exc:
                if not self._should_fallback_to_raw_events(exc):
                    raise
                rows = self._execute_query(_TRENDING_FALLBACK_QUERY, params)
            if not rows:
                rows = self._execute_query(_TRENDING_FALLBACK_QUERY, params)
            week_partition_days = max(
                1,
                (week_end.date() - week_start.date()).days + 1,
            )
            parquet_paths = self._parquet_query_paths(week_partition_days)
            if not rows and parquet_paths:
                rows = self._execute_parquet_query(
                    _PARQUET_TRENDING_QUERY,
                    [
                        parquet_paths,
                        week_start.date().isoformat(),
                        week_start,
                        week_end,
                        limit,
                    ],
                )
            results = []
            for rank, row in enumerate(rows, start=1):
                item = self._parse_repo_row(row)
                item["growth_rank"] = rank
                results.append(item)
            if not has_categorized_metadata:
                filtered_results = [
                    item for item in results if item["category"] != RepoCategory.OTHER.value
                ]
                if filtered_results:
                    return [
                        {**item, "growth_rank": rank}
                        for rank, item in enumerate(filtered_results[:limit], start=1)
                    ]
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
        """Return the strongest absolute and percentage-based movers in the window."""
        params: dict[str, Any] = {
            "days": days,
            "days_twice": max(days * 2, 2),
            "min_baseline_stars": min_baseline_stars,
        }
        has_metadata = self._repo_metadata_table_exists()
        absolute_query = (
            _SHOCK_MOVERS_ABSOLUTE_QUERY if has_metadata else _SHOCK_MOVERS_ABSOLUTE_FALLBACK_QUERY
        )
        percentage_query = (
            _SHOCK_MOVERS_PERCENTAGE_QUERY
            if has_metadata
            else _SHOCK_MOVERS_PERCENTAGE_FALLBACK_QUERY
        )

        def _run() -> dict[str, Any]:
            try:
                absolute_rows = self._execute_query(
                    absolute_query,
                    {**params, "limit": absolute_limit},
                )
            except DashboardQueryError as exc:
                if not self._should_fallback_to_raw_events(exc):
                    raise
                absolute_rows = self._execute_query(
                    _SHOCK_MOVERS_ABSOLUTE_FALLBACK_QUERY,
                    {**params, "limit": absolute_limit},
                )

            try:
                percentage_rows = self._execute_query(
                    percentage_query,
                    {**params, "limit": percentage_limit},
                )
            except DashboardQueryError as exc:
                if not self._should_fallback_to_raw_events(exc):
                    raise
                percentage_rows = self._execute_query(
                    _SHOCK_MOVERS_PERCENTAGE_FALLBACK_QUERY,
                    {**params, "limit": percentage_limit},
                )

            if not absolute_rows:
                absolute_rows = self._execute_query(
                    _SHOCK_MOVERS_ABSOLUTE_FALLBACK_QUERY,
                    {**params, "limit": absolute_limit},
                )
            if not percentage_rows:
                percentage_rows = self._execute_query(
                    _SHOCK_MOVERS_PERCENTAGE_FALLBACK_QUERY,
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
        """Return the topics gaining the most star momentum versus the prior window."""
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
        """Event counts grouped by GitHub topic tag.

        Args:
            days: Look-back window in days.

        Returns:
            List of dicts: ``{topic, event_count, repo_count}``.
        """
        params: dict[str, Any] = {"days": days}

        def _run() -> list[dict[str, Any]]:
            rows = self._execute_query(_TOPIC_BREAKDOWN_QUERY, params)
            parquet_paths = self._parquet_query_paths(days)
            if not rows and parquet_paths:
                rows = self._execute_parquet_query(
                    _PARQUET_TOPIC_BREAKDOWN_QUERY,
                    [parquet_paths, self._cutoff_date(days)],
                )
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
        """Event counts grouped by primary programming language.

        Args:
            days: Look-back window in days.

        Returns:
            List of dicts: ``{language, event_count, repo_count}``.
        """
        params: dict[str, Any] = {"days": days}

        def _run() -> list[dict[str, Any]]:
            rows = self._execute_query(_LANGUAGE_BREAKDOWN_QUERY, params)
            parquet_paths = self._parquet_query_paths(days)
            if not rows and parquet_paths:
                rows = self._execute_parquet_query(
                    _PARQUET_LANGUAGE_BREAKDOWN_QUERY,
                    [parquet_paths, self._cutoff_date(days)],
                )
            return [
                {
                    "language": str(row[0]),
                    "event_count": int(row[1]),
                    "repo_count": int(row[2]),
                }
                for row in rows
            ]

        return await asyncio.to_thread(_run)

    async def get_repo_timeseries(
        self,
        repo_name: str,
        days: int,
    ) -> list[dict[str, Any]]:
        """Daily star count + total event count for a specific repository.

        Args:
            repo_name: Repository in ``owner/repo`` format.
            days:      Look-back window in days.

        Returns:
            List of dicts: ``{event_date, star_count, total_events}``.
        """
        params: dict[str, Any] = {"repo_name": repo_name, "days": days}

        def _run() -> list[dict[str, Any]]:
            rows = self._execute_query(_REPO_TIMESERIES_QUERY, params)
            parquet_paths = self._parquet_query_paths(days)
            if not rows and parquet_paths:
                rows = self._execute_parquet_query(
                    _PARQUET_REPO_TIMESERIES_QUERY,
                    [parquet_paths, self._cutoff_date(days), repo_name],
                )
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
        """Per-category aggregate stats for the category summary cards.

        Returns:
            List of dicts: ``{category, repo_count, total_stars,
            top_repo_name, top_repo_stars, weekly_star_delta}``.
        """

        def _run() -> list[dict[str, Any]]:
            fallback_query = _CATEGORY_SUMMARY_FALLBACK_QUERY
            try:
                if self._has_categorized_repo_metadata():
                    rows = self._execute_query(_CATEGORY_SUMMARY_QUERY)
                else:
                    rows = self._execute_query(_CATEGORY_SUMMARY_SOURCE_FALLBACK_QUERY)
                    if rows:
                        return _build_category_summary_from_repo_rows(rows, self._classifier)
                    rows = self._execute_query(fallback_query)
            except DashboardQueryError as exc:
                if not self._should_fallback_to_raw_events(exc):
                    raise
                rows = self._execute_query(fallback_query)
            if not rows:
                rows = self._execute_query(fallback_query)
            parquet_paths = self._parquet_query_paths(7)
            if not rows and parquet_paths:
                rows = self._execute_parquet_query(
                    _PARQUET_CATEGORY_SUMMARY_QUERY,
                    [self._cutoff_date(7), parquet_paths],
                )
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


def _build_category_summary_from_repo_rows(
    rows: list[tuple[Any, ...]],
    classifier: CategoryClassifier,
) -> list[dict[str, Any]]:
    summaries: dict[str, dict[str, Any]] = {}
    for row in rows:
        topics_raw = row[6]
        topics: list[str] = list(topics_raw) if topics_raw else []
        category = str(
            classifier.classify(
                topics=topics,
                description=str(row[4]),
            )
        )
        if category == RepoCategory.OTHER.value:
            continue
        summary = summaries.setdefault(
            category,
            {
                "category": category,
                "repo_count": 0,
                "total_stars": 0,
                "top_repo_name": "",
                "top_repo_stars": 0,
                "weekly_star_delta": 0,
            },
        )
        stars = int(row[8])
        weekly_star_delta = int(row[19])
        summary["repo_count"] += 1
        summary["total_stars"] += stars
        summary["weekly_star_delta"] += weekly_star_delta
        if stars > int(summary["top_repo_stars"]):
            summary["top_repo_name"] = str(row[1])
            summary["top_repo_stars"] = stars

    return sorted(
        summaries.values(),
        key=lambda item: (
            int(item["total_stars"]),
            int(item["weekly_star_delta"]),
            int(item["repo_count"]),
        ),
        reverse=True,
    )
