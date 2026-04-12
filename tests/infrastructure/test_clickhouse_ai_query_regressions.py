"""Regression tests for ClickHouse fallback SQL used by AI services."""

from __future__ import annotations

from university.github.src.infrastructure.storage.clickhouse_ai_insights_service import (
    _REPO_ACTIVITY_BREAKDOWN_QUERY,
    _REPO_METADATA_FALLBACK_QUERY,
    _REPO_TIMESERIES_QUERY,
    _REPO_WINDOW_METRICS_QUERY,
)
from university.github.src.infrastructure.storage.clickhouse_ai_service import (
    _SEARCH_CANDIDATES_FALLBACK_QUERY,
)


def test_search_candidates_fallback_query_normalizes_full_repo_name() -> None:
    assert "lowerUTF8(repo_name) AS normalized_repo_name" in _SEARCH_CANDIDATES_FALLBACK_QUERY
    assert "GROUP BY normalized_repo_name" in _SEARCH_CANDIDATES_FALLBACK_QUERY
    assert "normalized_repo_name AS repo_full_name" in _SEARCH_CANDIDATES_FALLBACK_QUERY
    assert "concat('https://github.com/', normalized_repo_name) AS html_url" in (
        _SEARCH_CANDIDATES_FALLBACK_QUERY
    )


def test_repo_metadata_fallback_query_is_case_insensitive() -> None:
    assert "WHERE lowerUTF8(repo_name) = lowerUTF8(%(repo_name)s)" in (
        _REPO_METADATA_FALLBACK_QUERY
    )
    assert "normalized_repo_name AS repo_full_name" in _REPO_METADATA_FALLBACK_QUERY


def test_repo_context_queries_are_case_insensitive() -> None:
    predicate = "WHERE lowerUTF8(repo_name) = lowerUTF8(%(repo_name)s)"
    assert predicate in _REPO_WINDOW_METRICS_QUERY
    assert predicate in _REPO_ACTIVITY_BREAKDOWN_QUERY
    assert predicate in _REPO_TIMESERIES_QUERY
