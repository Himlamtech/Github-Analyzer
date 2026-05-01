"""ClickHouse-backed candidate retrieval for AI repository search."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any, cast

from clickhouse_driver import Client
from clickhouse_driver.errors import Error as ClickHouseError
from clickhouse_driver.errors import NetworkError as ClickHouseNetworkError

from src.application.dtos.ai_search_dto import RepoSearchCandidateDTO
from src.application.dtos.repo_metadata_dto import RepoMetadataDTO
from src.domain.exceptions import AISearchError, ClickHouseConnectionError
from src.domain.services.category_classifier import CategoryClassifier
from src.domain.value_objects.repo_category import RepoCategory

_SEARCH_CANDIDATES_QUERY = """
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
WHERE rm.stargazers_count >= %(min_stars)s
  AND (%(category)s = '' OR rm.category = %(category)s)
  AND (%(language)s = '' OR lowerUTF8(rm.primary_language) = lowerUTF8(%(language)s))
ORDER BY star_count_in_window DESC, rm.stargazers_count DESC, rm.github_pushed_at DESC
LIMIT %(limit)s
"""

_SEARCH_CANDIDATES_FALLBACK_QUERY = """
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
    WHERE repo_stargazers_count >= %(min_stars)s
      AND (%(language)s = '' OR lowerUTF8(repo_primary_language) = lowerUTF8(%(language)s))
) AS raw
GROUP BY normalized_repo_name
HAVING (%(category)s = '' OR %(category)s = 'Other')
ORDER BY star_count_in_window DESC, stargazers_count DESC, github_pushed_at DESC
LIMIT %(limit)s
"""


class ClickHouseAISearchService:
    """Load repository candidates from ClickHouse before application reranking."""

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
        params: dict[str, Any],
    ) -> list[tuple[Any, ...]]:
        client = self._get_client()
        try:
            rows = client.execute(query, params)
        except ClickHouseError as exc:
            raise AISearchError(f"AI search candidate query failed: {exc}") from exc
        return cast("list[tuple[Any, ...]]", rows)

    def _repo_metadata_table_exists(self) -> bool:
        rows = self._execute_query("EXISTS TABLE github_analyzer.repo_metadata", {})
        if not rows or not rows[0]:
            return False
        try:
            return int(rows[0][0]) == 1
        except (TypeError, ValueError):
            return True

    def _has_categorized_repo_metadata(self) -> bool:
        if self._has_categorized_metadata_cache is not None:
            return self._has_categorized_metadata_cache
        if not self._repo_metadata_table_exists():
            self._has_categorized_metadata_cache = False
            return False

        rows = self._execute_query(
            """
SELECT countIf(category != 'Other')
FROM github_analyzer.repo_metadata
FINAL
""",
            {},
        )
        try:
            self._has_categorized_metadata_cache = int(rows[0][0]) > 0
        except (IndexError, TypeError, ValueError):
            self._has_categorized_metadata_cache = True
        return self._has_categorized_metadata_cache

    def _parse_candidate_row(self, row: tuple[Any, ...]) -> RepoSearchCandidateDTO:
        topics_raw = row[6]
        topics = list(topics_raw) if topics_raw else []
        raw_category = str(row[7])
        effective_category = raw_category
        if raw_category == RepoCategory.OTHER.value:
            effective_category = str(
                self._classifier.classify(
                    topics=topics,
                    description=str(row[4]),
                )
            )
        repo = RepoMetadataDTO(
            repo_id=int(row[0]),
            repo_full_name=str(row[1]),
            repo_name=str(row[2]),
            html_url=str(row[3]),
            description=str(row[4]),
            primary_language=str(row[5]),
            topics=topics,
            category=effective_category,
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
        search_document = " ".join(
            part
            for part in [
                repo.repo_full_name,
                repo.repo_name,
                repo.owner_login,
                repo.primary_language,
                repo.category,
                " ".join(repo.topics),
                repo.description,
            ]
            if part
        )
        return RepoSearchCandidateDTO(
            repo=repo,
            star_count_in_window=int(row[19]),
            search_document=search_document[:1600],
        )

    async def get_candidates(
        self,
        *,
        category: str | None,
        primary_language: str | None,
        min_stars: int,
        days: int,
        limit: int,
    ) -> list[RepoSearchCandidateDTO]:
        """Return a candidate pool of repositories for the AI search use case."""
        params: dict[str, Any] = {
            "category": category or "",
            "language": primary_language or "",
            "min_stars": min_stars,
            "days": days,
            "limit": limit,
        }
        has_categorized_metadata = self._has_categorized_repo_metadata()
        query = (
            _SEARCH_CANDIDATES_QUERY
            if has_categorized_metadata
            else _SEARCH_CANDIDATES_FALLBACK_QUERY
        )
        if category and not has_categorized_metadata:
            params["category"] = ""
            params["limit"] = max(limit * 8, 40)

        def _run() -> list[RepoSearchCandidateDTO]:
            rows = self._execute_query(query, params)
            if not rows and query != _SEARCH_CANDIDATES_FALLBACK_QUERY:
                rows = self._execute_query(_SEARCH_CANDIDATES_FALLBACK_QUERY, params)
            candidates = [self._parse_candidate_row(row) for row in rows]
            if category:
                candidates = [
                    candidate for candidate in candidates if candidate.repo.category == category
                ]
            return candidates[:limit]

        return await asyncio.to_thread(_run)


def _coerce_datetime(value: object) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    return datetime.now(tz=UTC)
