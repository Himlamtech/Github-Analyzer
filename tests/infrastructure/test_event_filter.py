"""Unit tests for GitHub event admission filter."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from src.infrastructure.github.event_filter import PopularRepoFilter, RepositoryEventFilter


@pytest.fixture
def filter_() -> RepositoryEventFilter:
    return RepositoryEventFilter()


def _make_event(
    *,
    actor_login: str = "dev",
    repo_id: int = 123,
    repo_name: str = "owner/repo",
) -> dict[str, object]:
    return {
        "id": "evt_001",
        "type": "PushEvent",
        "actor": {"id": 1, "login": actor_login},
        "repo": {"id": repo_id, "name": repo_name},
        "payload": {},
        "created_at": datetime.now(tz=UTC).isoformat(),
        "public": True,
    }


def test_should_ingest_valid_event_returns_true(filter_: RepositoryEventFilter) -> None:
    assert filter_.should_ingest(_make_event()) is True


def test_should_ingest_bot_event_returns_true(filter_: RepositoryEventFilter) -> None:
    assert filter_.should_ingest(_make_event(actor_login="test[bot]")) is True


def test_should_ingest_missing_repo_identity_returns_false(filter_: RepositoryEventFilter) -> None:
    assert filter_.should_ingest(_make_event(repo_id=0, repo_name="")) is False


def test_should_ingest_missing_actor_returns_false(filter_: RepositoryEventFilter) -> None:
    assert filter_.should_ingest(_make_event(actor_login="")) is False


def test_popular_repo_filter_alias_points_to_repository_filter() -> None:
    assert PopularRepoFilter is RepositoryEventFilter
