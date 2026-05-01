"""Unit tests for ClickHouseDashboardService.

All ClickHouse I/O is mocked via ``unittest.mock.patch`` — no real DB connection.
Each test patches ``ClickHouseDashboardService._get_client`` to return a ``MagicMock``
whose ``.execute()`` returns pre-defined row tuples.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.domain.exceptions import ClickHouseConnectionError, DashboardQueryError
from src.infrastructure.storage.clickhouse_dashboard_service import (
    ClickHouseDashboardService,
)

# ── Helpers ───────────────────────────────────────────────────────────────────

_NOW = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)
_TODAY = date(2024, 6, 15)


def _make_service() -> ClickHouseDashboardService:
    return ClickHouseDashboardService(
        host="localhost",
        port=9000,
        user="default",
        password="",
        database="github_analyzer",
    )


_SENTINEL: list[str] = []  # used as a sentinel for the topics default


def _repo_row(
    repo_id: int = 1,
    full_name: str = "openai/gpt-5",
    name: str = "gpt-5",
    html_url: str = "https://github.com/openai/gpt-5",
    description: str = "GPT-5",
    language: str = "Python",
    topics: list[str] | None = None,
    category: str = "LLM",
    stars: int = 50000,
    watchers: int = 50000,
    forks: int = 3000,
    open_issues: int = 100,
    subscribers: int = 5000,
    owner_login: str = "openai",
    owner_avatar: str = "https://avatars.githubusercontent.com/u/14957082",
    license_name: str = "MIT License",
    created_at: datetime = _NOW,
    pushed_at: datetime = _NOW,
    rank: int = 1,
    star_count_in_window: int = 1000,
) -> tuple[Any, ...]:
    """Build a 20-element row tuple matching _parse_repo_row expectations."""
    resolved_topics: list[str] = ["llm", "transformer"] if topics is None else topics
    return (
        repo_id,  # 0: repo_id
        full_name,  # 1: repo_full_name
        name,  # 2: repo_name
        html_url,  # 3: html_url
        description,  # 4: description
        language,  # 5: primary_language
        resolved_topics,  # 6: topics
        category,  # 7: category
        stars,  # 8: stargazers_count
        watchers,  # 9: watchers_count
        forks,  # 10: forks_count
        open_issues,  # 11: open_issues_count
        subscribers,  # 12: subscribers_count
        owner_login,  # 13: owner_login
        owner_avatar,  # 14: owner_avatar_url
        license_name,  # 15: license_name
        created_at,  # 16: github_created_at
        pushed_at,  # 17: github_pushed_at
        rank,  # 18: rank
        star_count_in_window,  # 19: star_count_in_window
    )


def _mock_client(rows: list[tuple[Any, ...]]) -> MagicMock:
    """Return a MagicMock client whose .execute() always returns ``rows``."""
    client = MagicMock()
    client.execute.return_value = rows
    return client


def _mover_row(
    *,
    current_stars: int = 1_200,
    previous_stars: int = 300,
    unique_actors: int = 250,
    weekly_percent_gain: float = 12.5,
    window_over_window_ratio: float = 4.0,
    **repo_kwargs: object,
) -> tuple[Any, ...]:
    row = list(_repo_row(star_count_in_window=current_stars, **repo_kwargs))
    row.extend(
        [
            previous_stars,
            unique_actors,
            weekly_percent_gain,
            window_over_window_ratio,
        ]
    )
    return tuple(row)


# ── _parse_repo_row (static) ──────────────────────────────────────────────────


class TestParseRepoRow:
    def test_parse_repo_row_maps_all_fields(self) -> None:
        """All 20 columns must be mapped to the correct dict keys."""
        row = _repo_row()
        result = ClickHouseDashboardService._parse_repo_row(row)

        assert result["repo_id"] == 1
        assert result["repo_full_name"] == "openai/gpt-5"
        assert result["repo_name"] == "gpt-5"
        assert result["html_url"] == "https://github.com/openai/gpt-5"
        assert result["primary_language"] == "Python"
        assert result["category"] == "LLM"
        assert result["stargazers_count"] == 50000
        assert result["star_count_in_window"] == 1000

    def test_parse_repo_row_converts_topics_to_list(self) -> None:
        """Topics column (list/tuple from ClickHouse) must become a Python list."""
        row = _repo_row(topics=["llm", "agent"])
        result = ClickHouseDashboardService._parse_repo_row(row)

        assert isinstance(result["topics"], list)
        assert result["topics"] == ["llm", "agent"]

    def test_parse_repo_row_handles_empty_topics(self) -> None:
        """Empty topics column must produce an empty list, not raise."""
        row = _repo_row(topics=[])
        result = ClickHouseDashboardService._parse_repo_row(row)

        assert result["topics"] == []

    def test_parse_repo_row_handles_none_topics(self) -> None:
        """None topics column (NULL in ClickHouse) must produce an empty list."""
        row_list = list(_repo_row())
        row_list[6] = None  # topics = NULL
        result = ClickHouseDashboardService._parse_repo_row(tuple(row_list))

        assert result["topics"] == []

    def test_parse_repo_row_rank_as_int(self) -> None:
        """Rank must be cast to int even if ClickHouse returns it as a float."""
        row_list = list(_repo_row())
        row_list[18] = 3.0  # rank as float
        result = ClickHouseDashboardService._parse_repo_row(tuple(row_list))

        assert result["rank"] == 3
        assert isinstance(result["rank"], int)


# ── get_top_repos ─────────────────────────────────────────────────────────────


class TestGetTopRepos:
    async def test_get_top_repos_no_category_returns_list(self) -> None:
        """``category=None`` → uses all-repos query, returns parsed dicts."""
        svc = _make_service()
        rows = [_repo_row(), _repo_row(repo_id=2, full_name="anthropic/claude", name="claude")]

        with patch.object(svc, "_get_client", return_value=_mock_client(rows)):
            result = await svc.get_top_repos(category=None, days=7, limit=10)

        assert len(result) == 2
        assert result[0]["repo_full_name"] == "openai/gpt-5"
        assert result[1]["repo_full_name"] == "anthropic/claude"

    async def test_get_top_repos_queries_repo_metadata(self) -> None:
        """Top repo query must read from ``repo_metadata`` rather than raw event rows."""
        svc = _make_service()
        client = _mock_client([_repo_row()])

        with patch.object(svc, "_get_client", return_value=client):
            await svc.get_top_repos(category=None, days=7, limit=10)

        query_text = str(client.execute.call_args.args[0])
        assert "FROM repo_metadata AS rm" in query_text
        assert "INNER JOIN (" in query_text
        assert "ORDER BY star_count_in_window DESC, rm.stargazers_count DESC" in query_text

    async def test_get_top_repos_with_category_returns_filtered_list(self) -> None:
        """``category="LLM"`` → uses category-filtered query, returns parsed dicts."""
        svc = _make_service()
        rows = [_repo_row(category="LLM")]

        with patch.object(svc, "_get_client", return_value=_mock_client(rows)):
            result = await svc.get_top_repos(category="LLM", days=7, limit=5)

        assert len(result) == 1
        assert result[0]["category"] == "LLM"

    async def test_get_top_repos_empty_result(self) -> None:
        """Empty DB result → returns empty list (no errors)."""
        svc = _make_service()

        with (
            patch.object(svc, "_get_client", return_value=_mock_client([])),
            patch.object(svc, "_parquet_query_paths", return_value=[]),
        ):
            result = await svc.get_top_repos(category=None, days=7, limit=10)

        assert result == []

    async def test_get_top_repos_raises_dashboard_query_error_on_ch_failure(self) -> None:
        """ClickHouseError during execute → ``DashboardQueryError`` is raised."""
        from clickhouse_driver.errors import Error as ClickHouseError

        svc = _make_service()
        client = MagicMock()
        client.execute.side_effect = ClickHouseError("query failed")

        with (
            patch.object(svc, "_get_client", return_value=client),
            pytest.raises(DashboardQueryError, match="Dashboard query failed"),
        ):
            await svc.get_top_repos(category=None, days=7, limit=10)

    async def test_get_top_repos_falls_back_to_parquet_when_clickhouse_empty(self) -> None:
        svc = _make_service()
        parquet_rows = [_repo_row(full_name="org/repo-from-parquet", name="repo-from-parquet")]
        parquet_paths = ["data/raw/event_date=2024-06-15/event_type=*/*.parquet"]
        execute_parquet_query = MagicMock(return_value=parquet_rows)

        with (
            patch.object(svc, "_get_client", return_value=_mock_client([])),
            patch.object(svc, "_parquet_query_paths", return_value=parquet_paths),
            patch.object(svc, "_execute_parquet_query", execute_parquet_query),
        ):
            result = await svc.get_top_repos(category=None, days=7, limit=10)

        assert result[0]["repo_full_name"] == "org/repo-from-parquet"
        execute_parquet_query.assert_called_once()


class TestGetTopStarredRepos:
    async def test_get_top_starred_repos_queries_repo_metadata(self) -> None:
        svc = _make_service()
        client = _mock_client([_repo_row()])

        with patch.object(svc, "_get_client", return_value=client):
            await svc.get_top_starred_repos(category=None, days=7, limit=10)

        query_text = str(client.execute.call_args.args[0])
        assert "FROM repo_metadata AS rm" in query_text
        assert "ORDER BY rm.stargazers_count DESC, star_count_in_window DESC" in query_text

    async def test_get_top_starred_repos_returns_parsed_rows(self) -> None:
        svc = _make_service()
        rows = [_repo_row(full_name="org/most-starred", stars=999_999, star_count_in_window=3)]

        with patch.object(svc, "_get_client", return_value=_mock_client(rows)):
            result = await svc.get_top_starred_repos(category=None, days=7, limit=10)

        assert result[0]["repo_full_name"] == "org/most-starred"
        assert result[0]["stargazers_count"] == 999_999


# ── get_trending ──────────────────────────────────────────────────────────────


class TestGetTrending:
    async def test_get_trending_adds_growth_rank(self) -> None:
        """Each returned dict must include ``growth_rank`` starting at 1."""
        svc = _make_service()
        rows = [
            _repo_row(repo_id=1, full_name="org/repo-a", name="repo-a"),
            _repo_row(repo_id=2, full_name="org/repo-b", name="repo-b"),
            _repo_row(repo_id=3, full_name="org/repo-c", name="repo-c"),
        ]

        with patch.object(svc, "_get_client", return_value=_mock_client(rows)):
            result = await svc.get_trending(days=7, limit=3)

        assert [r["growth_rank"] for r in result] == [1, 2, 3]

    async def test_get_trending_empty_result(self) -> None:
        """Empty result → empty list with no errors."""
        svc = _make_service()

        with (
            patch.object(svc, "_get_client", return_value=_mock_client([])),
            patch.object(svc, "_parquet_query_paths", return_value=[]),
        ):
            result = await svc.get_trending(days=7, limit=10)

        assert result == []

    async def test_get_trending_returns_star_count_in_window(self) -> None:
        """Each trending repo must carry ``star_count_in_window`` from the query."""
        svc = _make_service()
        rows = [_repo_row(star_count_in_window=9999)]

        with patch.object(svc, "_get_client", return_value=_mock_client(rows)):
            result = await svc.get_trending(days=7, limit=5)

        assert result[0]["star_count_in_window"] == 9999

    async def test_get_trending_queries_repo_metadata(self) -> None:
        """Trending query must be backed by synced repo metadata."""
        svc = _make_service()
        client = _mock_client([_repo_row()])

        with patch.object(svc, "_get_client", return_value=client):
            await svc.get_trending(days=7, limit=5)

        query_text = str(client.execute.call_args.args[0])
        assert "FROM repo_metadata AS rm" in query_text
        assert "ORDER BY star_count_in_window DESC, rm.stargazers_count DESC" in query_text

    async def test_get_trending_falls_back_to_parquet_when_clickhouse_empty(self) -> None:
        svc = _make_service()
        parquet_rows = [_repo_row(full_name="org/parquet-trend", name="parquet-trend")]
        parquet_paths = ["data/raw/event_date=2024-06-15/event_type=*/*.parquet"]
        execute_parquet_query = MagicMock(return_value=parquet_rows)

        with (
            patch.object(svc, "_get_client", return_value=_mock_client([])),
            patch.object(svc, "_parquet_query_paths", return_value=parquet_paths),
            patch.object(svc, "_execute_parquet_query", execute_parquet_query),
        ):
            result = await svc.get_trending(days=7, limit=10)

        assert result[0]["repo_full_name"] == "org/parquet-trend"
        execute_parquet_query.assert_called_once()


class TestGetShockMovers:
    async def test_get_shock_movers_returns_absolute_and_percentage_lists(self) -> None:
        svc = _make_service()
        rows = [_mover_row(full_name="org/repo-a"), _mover_row(full_name="org/repo-b")]
        client = MagicMock()
        client.execute.side_effect = [
            [(1,)],
            rows,
            rows,
        ]

        with patch.object(svc, "_get_client", return_value=client):
            result = await svc.get_shock_movers(
                days=7,
                absolute_limit=2,
                percentage_limit=2,
                min_baseline_stars=1_000,
            )

        assert result["window_days"] == 7
        assert result["absolute_movers"][0]["repo_full_name"] == "org/repo-a"
        assert result["absolute_movers"][0]["previous_star_count_in_window"] == 300
        assert result["percentage_movers"][1]["repo_full_name"] == "org/repo-b"

    async def test_get_shock_movers_falls_back_to_raw_when_metadata_query_fails(self) -> None:
        svc = _make_service()
        client = MagicMock()
        client.execute.side_effect = [
            [(1,)],
            DashboardQueryError("repo_metadata UNKNOWN_TABLE"),
            [_mover_row(full_name="org/raw-repo")],
            DashboardQueryError("repo_metadata UNKNOWN_TABLE"),
            [_mover_row(full_name="org/raw-repo")],
        ]

        with patch.object(svc, "_get_client", return_value=client):
            result = await svc.get_shock_movers(
                days=7,
                absolute_limit=1,
                percentage_limit=1,
                min_baseline_stars=1_000,
            )

        assert result["absolute_movers"][0]["repo_full_name"] == "org/raw-repo"
        assert result["percentage_movers"][0]["repo_full_name"] == "org/raw-repo"


class TestGetTopicRotation:
    async def test_get_topic_rotation_returns_ranked_topic_rows(self) -> None:
        svc = _make_service()
        rows = [
            ("browser-use", 600, 120, 14),
            ("coding-agents", 420, 210, 11),
        ]
        client = MagicMock()
        client.execute.return_value = rows

        with patch.object(svc, "_get_client", return_value=client):
            result = await svc.get_topic_rotation(days=7, limit=8)

        assert result == [
            {
                "topic": "browser-use",
                "current_star_count": 600,
                "previous_star_count": 120,
                "star_delta": 480,
                "repo_count": 14,
                "rank": 1,
            },
            {
                "topic": "coding-agents",
                "current_star_count": 420,
                "previous_star_count": 210,
                "star_delta": 210,
                "repo_count": 11,
                "rank": 2,
            },
        ]

    async def test_get_topic_rotation_uses_subquery_array_join_shape(self) -> None:
        svc = _make_service()
        client = _mock_client([("agents", 1, 0, 1)])

        with patch.object(svc, "_get_client", return_value=client):
            await svc.get_topic_rotation(days=7, limit=8)

        query_text = str(client.execute.call_args.args[0])
        assert "arrayJoin(repo_topics) AS topic" in query_text
        assert "FROM github_analyzer.github_data" in query_text


# ── get_topic_breakdown ────────────────────────────────────────────────────────


class TestGetTopicBreakdown:
    async def test_get_topic_breakdown_returns_correct_structure(self) -> None:
        """Result dicts must contain topic, event_count, repo_count."""
        svc = _make_service()
        ch_rows: list[tuple[Any, ...]] = [
            ("llm", 5000, 20),
            ("transformer", 3000, 15),
            ("agent", 2500, 10),
        ]

        with patch.object(svc, "_get_client", return_value=_mock_client(ch_rows)):
            result = await svc.get_topic_breakdown(days=7)

        assert len(result) == 3
        assert result[0] == {"topic": "llm", "event_count": 5000, "repo_count": 20}
        assert result[1] == {"topic": "transformer", "event_count": 3000, "repo_count": 15}

    async def test_get_topic_breakdown_empty_result(self) -> None:
        """Empty DB result → empty list."""
        svc = _make_service()

        with (
            patch.object(svc, "_get_client", return_value=_mock_client([])),
            patch.object(svc, "_parquet_query_paths", return_value=[]),
        ):
            result = await svc.get_topic_breakdown(days=7)

        assert result == []

    async def test_get_topic_breakdown_casts_types(self) -> None:
        """event_count and repo_count must be integers even if CH returns float."""
        svc = _make_service()
        ch_rows: list[tuple[Any, ...]] = [("llm", 5000.0, 20.0)]

        with patch.object(svc, "_get_client", return_value=_mock_client(ch_rows)):
            result = await svc.get_topic_breakdown(days=7)

        assert isinstance(result[0]["event_count"], int)
        assert isinstance(result[0]["repo_count"], int)

    async def test_get_topic_breakdown_counts_watch_events_only(self) -> None:
        svc = _make_service()
        client = _mock_client([("llm", 5, 2)])

        with patch.object(svc, "_get_client", return_value=client):
            await svc.get_topic_breakdown(days=7)

        query_text = str(client.execute.call_args.args[0])
        assert "countIf(gd.event_type = 'WatchEvent')" in query_text

    async def test_get_topic_breakdown_falls_back_to_parquet_when_clickhouse_empty(self) -> None:
        svc = _make_service()
        parquet_rows: list[tuple[Any, ...]] = [("llm", 12, 3)]
        parquet_paths = ["data/raw/event_date=2024-06-15/event_type=*/*.parquet"]

        with (
            patch.object(svc, "_get_client", return_value=_mock_client([])),
            patch.object(svc, "_parquet_query_paths", return_value=parquet_paths),
            patch.object(svc, "_execute_parquet_query", return_value=parquet_rows),
        ):
            result = await svc.get_topic_breakdown(days=7)

        assert result == [{"topic": "llm", "event_count": 12, "repo_count": 3}]


# ── get_language_breakdown ────────────────────────────────────────────────────


class TestGetLanguageBreakdown:
    async def test_get_language_breakdown_returns_correct_structure(self) -> None:
        """Result dicts must contain language, event_count, repo_count."""
        svc = _make_service()
        ch_rows: list[tuple[Any, ...]] = [
            ("Python", 10000, 50),
            ("Rust", 3000, 12),
        ]

        with patch.object(svc, "_get_client", return_value=_mock_client(ch_rows)):
            result = await svc.get_language_breakdown(days=7)

        assert len(result) == 2
        assert result[0] == {"language": "Python", "event_count": 10000, "repo_count": 50}

    async def test_get_language_breakdown_empty_result(self) -> None:
        """Empty DB result → empty list."""
        svc = _make_service()

        with (
            patch.object(svc, "_get_client", return_value=_mock_client([])),
            patch.object(svc, "_parquet_query_paths", return_value=[]),
        ):
            result = await svc.get_language_breakdown(days=7)

        assert result == []

    async def test_get_language_breakdown_counts_watch_events_only(self) -> None:
        svc = _make_service()
        client = _mock_client([("Python", 10, 3)])

        with patch.object(svc, "_get_client", return_value=client):
            await svc.get_language_breakdown(days=7)

        query_text = str(client.execute.call_args.args[0])
        assert "countIf(gd.event_type = 'WatchEvent')" in query_text


# ── get_repo_timeseries ───────────────────────────────────────────────────────


class TestGetRepoTimeseries:
    async def test_get_repo_timeseries_returns_daily_points(self) -> None:
        """Each row must map to event_date, star_count, total_events."""
        svc = _make_service()
        d1 = date(2024, 6, 13)
        d2 = date(2024, 6, 14)
        d3 = date(2024, 6, 15)
        ch_rows: list[tuple[Any, ...]] = [
            (d1, 100, 500),
            (d2, 150, 700),
            (d3, 200, 900),
        ]

        with patch.object(svc, "_get_client", return_value=_mock_client(ch_rows)):
            result = await svc.get_repo_timeseries(repo_name="openai/gpt-5", days=7)

        assert len(result) == 3
        assert result[0]["event_date"] == d1
        assert result[0]["star_count"] == 100
        assert result[0]["total_events"] == 500
        assert result[2]["star_count"] == 200

    async def test_get_repo_timeseries_empty_result(self) -> None:
        """No data for requested repo+days → empty list."""
        svc = _make_service()

        with (
            patch.object(svc, "_get_client", return_value=_mock_client([])),
            patch.object(svc, "_parquet_query_paths", return_value=[]),
        ):
            result = await svc.get_repo_timeseries(repo_name="nobody/norepo", days=7)

        assert result == []

    async def test_get_repo_timeseries_casts_counts_to_int(self) -> None:
        """star_count and total_events must be integers."""
        svc = _make_service()
        ch_rows: list[tuple[Any, ...]] = [(_TODAY, 100.0, 500.0)]

        with patch.object(svc, "_get_client", return_value=_mock_client(ch_rows)):
            result = await svc.get_repo_timeseries(repo_name="org/repo", days=7)

        assert isinstance(result[0]["star_count"], int)
        assert isinstance(result[0]["total_events"], int)


# ── get_category_summary ──────────────────────────────────────────────────────


class TestGetCategorySummary:
    async def test_get_category_summary_returns_all_categories(self) -> None:
        """Result must contain one dict per category with the expected keys."""
        svc = _make_service()
        ch_rows: list[tuple[Any, ...]] = [
            ("LLM", 45, 2500000, "openai/gpt-5", 50000, 12000),
            ("Agent", 30, 800000, "langchain-ai/langchain", 30000, 5000),
            ("Diffusion", 15, 400000, "stability-ai/stable-diffusion", 20000, 3000),
        ]

        with patch.object(svc, "_get_client", return_value=_mock_client(ch_rows)):
            result = await svc.get_category_summary()

        assert len(result) == 3
        assert result[0]["category"] == "LLM"
        assert result[0]["repo_count"] == 45
        assert result[0]["total_stars"] == 2500000
        assert result[0]["top_repo_name"] == "openai/gpt-5"
        assert result[0]["top_repo_stars"] == 50000
        assert result[0]["weekly_star_delta"] == 12000

    async def test_get_category_summary_empty_result(self) -> None:
        """No data → empty list without errors."""
        svc = _make_service()

        with (
            patch.object(svc, "_get_client", return_value=_mock_client([])),
            patch.object(svc, "_parquet_query_paths", return_value=[]),
        ):
            result = await svc.get_category_summary()

        assert result == []

    async def test_get_category_summary_casts_all_ints(self) -> None:
        """All numeric fields must be cast to int."""
        svc = _make_service()
        ch_rows: list[tuple[Any, ...]] = [
            ("LLM", 45.0, 2500000.0, "openai/gpt-5", 50000.0, 12000.0),
        ]

        with patch.object(svc, "_get_client", return_value=_mock_client(ch_rows)):
            result = await svc.get_category_summary()

        assert isinstance(result[0]["repo_count"], int)
        assert isinstance(result[0]["total_stars"], int)
        assert isinstance(result[0]["top_repo_stars"], int)
        assert isinstance(result[0]["weekly_star_delta"], int)

    async def test_get_category_summary_falls_back_to_parquet_when_clickhouse_empty(self) -> None:
        svc = _make_service()
        parquet_rows: list[tuple[Any, ...]] = [("Other", 5, 1000, "org/repo", 500, 10)]
        parquet_paths = ["data/raw/event_date=2024-06-15/event_type=*/*.parquet"]

        with (
            patch.object(svc, "_get_client", return_value=_mock_client([])),
            patch.object(svc, "_parquet_query_paths", return_value=parquet_paths),
            patch.object(svc, "_execute_parquet_query", return_value=parquet_rows),
        ):
            result = await svc.get_category_summary()

        assert result[0]["category"] == "Other"
        assert result[0]["repo_count"] == 5


# ── _get_client error path ────────────────────────────────────────────────────


class TestGetClientErrorHandling:
    def test_get_client_raises_connection_error_on_network_failure(self) -> None:
        """ClickHouseNetworkError during Client() must raise ClickHouseConnectionError."""
        from clickhouse_driver.errors import NetworkError as ClickHouseNetworkError

        svc = _make_service()

        with (
            patch(
                "src.infrastructure.storage.clickhouse_dashboard_service.Client",
                side_effect=ClickHouseNetworkError("connection refused"),
            ),
            pytest.raises(ClickHouseConnectionError, match="Cannot connect to ClickHouse"),
        ):
            svc._get_client()

    async def test_all_async_methods_propagate_dashboard_query_error(self) -> None:
        """DashboardQueryError from _execute_query must surface in every async method."""
        from clickhouse_driver.errors import Error as ClickHouseError

        svc = _make_service()
        client = MagicMock()
        client.execute.side_effect = ClickHouseError("query error")

        with (
            patch.object(svc, "_get_client", return_value=client),
            pytest.raises(DashboardQueryError),
        ):
            await svc.get_top_repos(category=None, days=7, limit=10)

        with (
            patch.object(svc, "_get_client", return_value=client),
            pytest.raises(DashboardQueryError),
        ):
            await svc.get_trending(days=7, limit=10)

        with (
            patch.object(svc, "_get_client", return_value=client),
            pytest.raises(DashboardQueryError),
        ):
            await svc.get_topic_breakdown(days=7)

        with (
            patch.object(svc, "_get_client", return_value=client),
            pytest.raises(DashboardQueryError),
        ):
            await svc.get_language_breakdown(days=7)

        with (
            patch.object(svc, "_get_client", return_value=client),
            pytest.raises(DashboardQueryError),
        ):
            await svc.get_repo_timeseries(repo_name="org/repo", days=7)

        with (
            patch.object(svc, "_get_client", return_value=client),
            pytest.raises(DashboardQueryError),
        ):
            await svc.get_category_summary()
