"""Regression tests for ClickHouse dashboard fallback SQL."""

from __future__ import annotations

from src.infrastructure.storage.clickhouse_dashboard_service import (
    _TOP_REPOS_ALL_FALLBACK_QUERY,
    _TOP_REPOS_CATEGORY_FALLBACK_QUERY,
    _TOP_STARRED_REPOS_ALL_FALLBACK_QUERY,
    _TOP_STARRED_REPOS_CATEGORY_FALLBACK_QUERY,
    _TRENDING_FALLBACK_QUERY,
)


def test_top_repos_fallback_query_normalizes_repo_full_name() -> None:
    assert "lowerUTF8(repo_name) AS normalized_repo_name" in _TOP_REPOS_ALL_FALLBACK_QUERY
    assert "GROUP BY normalized_repo_name" in _TOP_REPOS_ALL_FALLBACK_QUERY
    assert "normalized_repo_name AS repo_full_name" in _TOP_REPOS_ALL_FALLBACK_QUERY
    assert "concat('https://github.com/', normalized_repo_name) AS html_url" in (
        _TOP_REPOS_ALL_FALLBACK_QUERY
    )
    assert "ORDER BY star_count_in_window DESC, any(repo_stargazers_count) DESC" in (
        _TOP_REPOS_ALL_FALLBACK_QUERY
    )


def test_top_repos_category_fallback_query_normalizes_repo_full_name() -> None:
    assert "lowerUTF8(repo_name) AS normalized_repo_name" in _TOP_REPOS_CATEGORY_FALLBACK_QUERY
    assert "GROUP BY normalized_repo_name" in _TOP_REPOS_CATEGORY_FALLBACK_QUERY
    assert "normalized_repo_name AS repo_full_name" in _TOP_REPOS_CATEGORY_FALLBACK_QUERY
    assert "ORDER BY star_count_in_window DESC, any(repo_stargazers_count) DESC" in (
        _TOP_REPOS_CATEGORY_FALLBACK_QUERY
    )


def test_top_starred_repos_fallback_query_normalizes_repo_full_name() -> None:
    assert "lowerUTF8(repo_name) AS normalized_repo_name" in _TOP_STARRED_REPOS_ALL_FALLBACK_QUERY
    assert "GROUP BY normalized_repo_name" in _TOP_STARRED_REPOS_ALL_FALLBACK_QUERY
    assert "normalized_repo_name AS repo_full_name" in _TOP_STARRED_REPOS_ALL_FALLBACK_QUERY
    assert "ORDER BY any(repo_stargazers_count) DESC, star_count_in_window DESC" in (
        _TOP_STARRED_REPOS_ALL_FALLBACK_QUERY
    )


def test_top_starred_repos_category_fallback_query_normalizes_repo_full_name() -> None:
    assert "lowerUTF8(repo_name) AS normalized_repo_name" in (
        _TOP_STARRED_REPOS_CATEGORY_FALLBACK_QUERY
    )
    assert "GROUP BY normalized_repo_name" in _TOP_STARRED_REPOS_CATEGORY_FALLBACK_QUERY
    assert "normalized_repo_name AS repo_full_name" in _TOP_STARRED_REPOS_CATEGORY_FALLBACK_QUERY
    assert "ORDER BY any(repo_stargazers_count) DESC, star_count_in_window DESC" in (
        _TOP_STARRED_REPOS_CATEGORY_FALLBACK_QUERY
    )


def test_trending_fallback_query_normalizes_repo_full_name() -> None:
    assert "lowerUTF8(repo_name) AS normalized_repo_name" in _TRENDING_FALLBACK_QUERY
    assert "GROUP BY normalized_repo_name" in _TRENDING_FALLBACK_QUERY
    assert "normalized_repo_name AS repo_full_name" in _TRENDING_FALLBACK_QUERY
