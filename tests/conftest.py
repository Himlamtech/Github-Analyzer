"""Shared pytest fixtures for the GitHub AI Trend Analyzer test suite."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from src.domain.entities.github_event import GithubEvent
from src.domain.value_objects.event_type import EventType
from src.domain.value_objects.repository_id import RepositoryId


@pytest.fixture
def utc_now() -> datetime:
    """Return a timezone-aware UTC datetime for use in tests."""
    return datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def sample_repo_id() -> RepositoryId:
    """Return a valid RepositoryId for testing."""
    return RepositoryId.from_api(repo_id=123456, repo_name="openai/gpt-5")


@pytest.fixture
def sample_github_event(utc_now: datetime, sample_repo_id: RepositoryId) -> GithubEvent:
    """Return a fully constructed GithubEvent aggregate for testing."""
    return GithubEvent(
        event_id="evt_001",
        event_type=EventType.WATCH,
        repo_id=sample_repo_id,
        actor_id=9999,
        actor_login="ml_researcher",
        created_at=utc_now,
        payload={"action": "started"},
        public=True,
    )


@pytest.fixture
def raw_watch_event(utc_now: datetime) -> dict[str, Any]:
    """Return a raw GitHub API event dict resembling a WatchEvent."""
    return {
        "id": "evt_001",
        "type": "WatchEvent",
        "actor": {"id": 9999, "login": "ml_researcher"},
        "repo": {"id": 123456, "name": "openai/gpt-5"},
        "payload": {"action": "started"},
        "created_at": utc_now.isoformat(),
        "public": True,
    }


@pytest.fixture
def raw_bot_event(utc_now: datetime) -> dict[str, Any]:
    """Return a raw GitHub API event with a bot actor login."""
    return {
        "id": "evt_bot_001",
        "type": "PushEvent",
        "actor": {"id": 1111, "login": "dependabot[bot]"},
        "repo": {"id": 123456, "name": "openai/gpt-5"},
        "payload": {},
        "created_at": utc_now.isoformat(),
        "public": True,
    }
