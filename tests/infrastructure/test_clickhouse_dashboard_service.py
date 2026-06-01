"""Unit tests for ClickHouseDashboardService."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.domain.exceptions import ClickHouseConnectionError, DashboardQueryError
from src.infrastructure.storage.clickhouse_dashboard_service import (
    ClickHouseDashboardService,
)

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
    resolved_topics: list[str] = ["llm", "transformer"] if topics is None else topics
    return (
        repo_id,
        full_name,
        name,
        html_url,
        description,
        language,
        resolved_topics,
        category,
        stars,
        watchers,
        forks,
        open_issues,
        subscribers,
        owner_login,
        owner_avatar,
        license_name,
        created_at,
        pushed_at,
        rank,
        star_count_in_window,
    )


def _mock_client(rows: list[tuple[Any, ...]]) -> MagicMock:
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


class TestParseRepoRow:
    def test_parse_repo_row_maps_all_fields(self) -> None:
        result = ClickHouseDashboardService._parse_repo_row(_repo_row())

        assert result["repo_id"] == 1
        assert result["repo_full_name"] == "openai/gpt-5"
        assert result["repo_name"] == "gpt-5"
        assert result["html_url"] == "https://github.com/openai/gpt-5"
        assert result["primary_language"] == "Python"
        assert result["category"] == "LLM"
        assert result["stargazers_count"] == 50000
        assert result["star_count_in_window"] == 1000

    def test_parse_repo_row_handles_none_topics(self) -> None:
        row = list(_repo_row())
        row[6] = None

        result = ClickHouseDashboardService._parse_repo_row(tuple(row))

        assert result["topics"] == []

    def test_parse_repo_row_rank_as_int(self) -> None:
        row = list(_repo_row())
        row[18] = 3.0

        result = ClickHouseDashboardService._parse_repo_row(tuple(row))

        assert result["rank"] == 3
        assert isinstance(result["rank"], int)


class TestGetTopRepos:
    async def test_get_top_repos_no_category_returns_list(self) -> None:
        svc = _make_service()
        rows = [_repo_row(), _repo_row(repo_id=2, full_name="anthropic/claude", name="claude")]

        with patch.object(svc, "_get_client", return_value=_mock_client(rows)):
            result = await svc.get_top_repos(category=None, days=7, limit=10)

        assert len(result) == 2
        assert result[0]["repo_full_name"] == "openai/gpt-5"
        assert result[1]["repo_full_name"] == "anthropic/claude"

    async def test_get_top_repos_queries_repo_metadata(self) -> None:
        svc = _make_service()
        client = _mock_client([_repo_row()])

        with patch.object(svc, "_get_client", return_value=client):
            await svc.get_top_repos(category=None, days=7, limit=10)

        query_text = str(client.execute.call_args.args[0])
        assert "FROM repo_metadata AS rm" in query_text
        assert "INNER JOIN (" in query_text
        assert "ORDER BY star_count_in_window DESC, rm.stargazers_count DESC" in query_text

    async def test_get_top_repos_empty_result(self) -> None:
        svc = _make_service()

        with (
            patch.object(svc, "_repo_metadata_table_exists", return_value=True),
            patch.object(svc, "_get_client", return_value=_mock_client([])),
        ):
            result = await svc.get_top_repos(category=None, days=7, limit=10)

        assert result == []

    async def test_get_top_repos_raises_when_repo_metadata_is_missing(self) -> None:
        svc = _make_service()

        with (
            patch.object(svc, "_repo_metadata_table_exists", return_value=False),
            pytest.raises(DashboardQueryError, match="repo_metadata table is required"),
        ):
            await svc.get_top_repos(category=None, days=7, limit=10)


class TestGetTopStarredRepos:
    async def test_get_top_starred_repos_queries_repo_metadata(self) -> None:
        svc = _make_service()
        client = _mock_client([_repo_row()])

        with patch.object(svc, "_get_client", return_value=client):
            await svc.get_top_starred_repos(category=None, limit=10)

        query_text = str(client.execute.call_args.args[0])
        assert "FROM repo_metadata AS rm" in query_text
        assert "toInt64(0) AS star_count_in_window" in query_text
        assert "ORDER BY rm.stargazers_count DESC, rm.repo_full_name ASC" in query_text

    async def test_get_top_starred_repos_returns_parsed_rows(self) -> None:
        svc = _make_service()
        rows = [_repo_row(full_name="org/most-starred", stars=999_999, star_count_in_window=3)]

        with patch.object(svc, "_get_client", return_value=_mock_client(rows)):
            result = await svc.get_top_starred_repos(category=None, limit=10)

        assert result[0]["repo_full_name"] == "org/most-starred"
        assert result[0]["stargazers_count"] == 999_999

    async def test_get_top_starred_repos_raises_when_repo_metadata_is_missing(self) -> None:
        svc = _make_service()

        with (
            patch.object(svc, "_repo_metadata_table_exists", return_value=False),
            pytest.raises(DashboardQueryError, match="repo_metadata table is required"),
        ):
            await svc.get_top_starred_repos(category=None, limit=10)


class TestGetTrending:
    async def test_get_trending_adds_growth_rank(self) -> None:
        svc = _make_service()
        rows = [
            _repo_row(repo_id=1, full_name="org/repo-a", name="repo-a"),
            _repo_row(repo_id=2, full_name="org/repo-b", name="repo-b"),
            _repo_row(repo_id=3, full_name="org/repo-c", name="repo-c"),
        ]

        with patch.object(svc, "_get_client", return_value=_mock_client(rows)):
            result = await svc.get_trending(days=7, limit=3)

        assert [r["growth_rank"] for r in result] == [1, 2, 3]

    async def test_get_trending_queries_repo_metadata_history(self) -> None:
        svc = _make_service()
        client = _mock_client([_repo_row()])
        week_start = datetime(2026, 5, 3, 17, 0, tzinfo=UTC)
        week_end = datetime(2026, 5, 4, 6, 0, tzinfo=UTC)

        with (
            patch.object(svc, "_get_client", return_value=client),
            patch.object(svc, "_current_gmt7_week_bounds", return_value=(week_start, week_end)),
        ):
            await svc.get_trending(days=7, limit=5)

        query_text = str(client.execute.call_args.args[0])
        params = client.execute.call_args.args[1]
        assert "FROM repo_metadata_history" in query_text
        assert "snapshot_at >= %(week_start)s" in query_text
        assert "snapshot_at < %(week_end)s" in query_text
        assert "latest.repo_full_name AS repo_full_name" in query_text
        assert "latest.*" not in query_text
        assert params["week_start"] == week_start
        assert params["week_end"] == week_end

    async def test_get_trending_raises_when_repo_metadata_history_is_missing(self) -> None:
        svc = _make_service()

        with (
            patch.object(svc, "_repo_metadata_history_table_exists", return_value=False),
            pytest.raises(DashboardQueryError, match="repo_metadata_history table is required"),
        ):
            await svc.get_trending(days=7, limit=5)

    def test_current_gmt7_week_bounds_start_on_monday_local_time(self) -> None:
        now = datetime(2026, 5, 4, 6, 0, tzinfo=UTC)

        week_start, week_end = ClickHouseDashboardService._current_gmt7_week_bounds(now)

        assert week_start == datetime(2026, 5, 3, 17, 0, tzinfo=UTC)
        assert week_end == now


class TestGetShockMovers:
    async def test_get_shock_movers_returns_absolute_and_percentage_lists(self) -> None:
        svc = _make_service()
        rows = [_mover_row(full_name="org/repo-a"), _mover_row(full_name="org/repo-b")]
        client = MagicMock()
        client.execute.side_effect = [[(1,)], rows, rows]

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

    async def test_get_shock_movers_raises_when_repo_metadata_is_missing(self) -> None:
        svc = _make_service()

        with (
            patch.object(svc, "_repo_metadata_table_exists", return_value=False),
            pytest.raises(DashboardQueryError, match="repo_metadata table is required"),
        ):
            await svc.get_shock_movers(
                days=7,
                absolute_limit=1,
                percentage_limit=1,
                min_baseline_stars=1_000,
            )


class TestGetTopicRotation:
    async def test_get_topic_rotation_returns_ranked_topic_rows(self) -> None:
        svc = _make_service()
        rows = [("browser-use", 600, 120, 14), ("coding-agents", 420, 210, 11)]

        with patch.object(svc, "_get_client", return_value=_mock_client(rows)):
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


class TestGetTopicBreakdown:
    async def test_get_topic_breakdown_returns_correct_structure(self) -> None:
        svc = _make_service()
        rows = [("llm", 5000, 20), ("transformer", 3000, 15)]

        with patch.object(svc, "_get_client", return_value=_mock_client(rows)):
            result = await svc.get_topic_breakdown(days=7)

        assert result[0] == {"topic": "llm", "event_count": 5000, "repo_count": 20}
        assert result[1] == {"topic": "transformer", "event_count": 3000, "repo_count": 15}

    async def test_get_topic_breakdown_empty_result(self) -> None:
        svc = _make_service()

        with patch.object(svc, "_get_client", return_value=_mock_client([])):
            result = await svc.get_topic_breakdown(days=7)

        assert result == []


class TestGetLanguageBreakdown:
    async def test_get_language_breakdown_returns_correct_structure(self) -> None:
        svc = _make_service()
        rows = [("Python", 10000, 50), ("Rust", 3000, 12)]

        with patch.object(svc, "_get_client", return_value=_mock_client(rows)):
            result = await svc.get_language_breakdown(days=7)

        assert result[0] == {"language": "Python", "event_count": 10000, "repo_count": 50}

    async def test_get_language_breakdown_empty_result(self) -> None:
        svc = _make_service()

        with patch.object(svc, "_get_client", return_value=_mock_client([])):
            result = await svc.get_language_breakdown(days=7)

        assert result == []


class TestGetRepoTimeseries:
    async def test_get_repo_timeseries_returns_daily_points(self) -> None:
        svc = _make_service()
        rows = [(_TODAY, 100, 500), (_TODAY, 150, 700)]

        with patch.object(svc, "_get_client", return_value=_mock_client(rows)):
            result = await svc.get_repo_timeseries(repo_name="openai/gpt-5", days=7)

        assert result[0]["event_date"] == _TODAY
        assert result[0]["star_count"] == 100
        assert result[1]["total_events"] == 700

    async def test_get_repo_timeseries_empty_result(self) -> None:
        svc = _make_service()

        with patch.object(svc, "_get_client", return_value=_mock_client([])):
            result = await svc.get_repo_timeseries(repo_name="nobody/norepo", days=7)

        assert result == []


class TestGetCategorySummary:
    async def test_get_category_summary_returns_all_categories(self) -> None:
        svc = _make_service()
        rows = [
            ("LLM", 45, 2500000, "openai/gpt-5", 50000, 12000),
            ("Agent", 30, 800000, "langchain-ai/langchain", 30000, 5000),
        ]

        with patch.object(svc, "_get_client", return_value=_mock_client(rows)):
            result = await svc.get_category_summary()

        assert result[0]["category"] == "LLM"
        assert result[0]["repo_count"] == 45
        assert result[0]["weekly_star_delta"] == 12000

    async def test_get_category_summary_raises_when_repo_metadata_is_missing(self) -> None:
        svc = _make_service()

        with (
            patch.object(svc, "_repo_metadata_table_exists", return_value=False),
            pytest.raises(DashboardQueryError, match="repo_metadata table is required"),
        ):
            await svc.get_category_summary()


class TestGetClientErrorHandling:
    def test_get_client_raises_connection_error_on_network_failure(self) -> None:
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
