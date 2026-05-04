"""Unit tests for the GithubEvent aggregate root."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from src.domain.entities.github_event import GithubEvent
from src.domain.exceptions import ValidationError
from src.domain.value_objects.event_type import EventType
from src.domain.value_objects.repository_id import RepositoryId


def _make_event(**overrides: object) -> GithubEvent:
    """Factory helper that produces a valid GithubEvent with optional overrides."""
    defaults: dict[str, object] = {
        "event_id": "test_event_1",
        "event_type": EventType.WATCH,
        "repo_id": RepositoryId.from_api(repo_id=1, repo_name="owner/repo"),
        "actor_id": 42,
        "actor_login": "test_user",
        "created_at": datetime(2024, 1, 1, tzinfo=UTC),
        "payload": {},
        "public": True,
    }
    defaults.update(overrides)
    return GithubEvent(**defaults)  # type: ignore[arg-type]


class TestGithubEventCreation:
    """Tests for valid and invalid GithubEvent construction."""

    def test_create_valid_event_succeeds(self) -> None:
        """Happy path: valid event is created without errors."""
        event = _make_event()
        assert event.event_id == "test_event_1"
        assert event.event_type == EventType.WATCH
        assert event.actor_login == "test_user"

    def test_empty_event_id_raises_validation_error(self) -> None:
        """Edge case: empty event_id must raise ValidationError."""
        with pytest.raises(ValidationError, match="event_id must be a non-empty string"):
            _make_event(event_id="")

    def test_whitespace_event_id_raises_validation_error(self) -> None:
        """Edge case: whitespace-only event_id must raise ValidationError."""
        with pytest.raises(ValidationError):
            _make_event(event_id="   ")

    def test_non_positive_actor_id_raises_validation_error(self) -> None:
        """Edge case: actor_id <= 0 must raise ValidationError."""
        with pytest.raises(ValidationError, match="actor_id must be a positive integer"):
            _make_event(actor_id=0)

    def test_negative_actor_id_raises_validation_error(self) -> None:
        """Edge case: negative actor_id must raise ValidationError."""
        with pytest.raises(ValidationError):
            _make_event(actor_id=-1)

    def test_empty_actor_login_raises_validation_error(self) -> None:
        """Edge case: empty actor_login must raise ValidationError."""
        with pytest.raises(ValidationError, match="actor_login must be a non-empty string"):
            _make_event(actor_login="")

    def test_naive_created_at_raises_validation_error(self) -> None:
        """Edge case: naive (no tzinfo) datetime must raise ValidationError."""
        naive_dt = datetime(2024, 1, 1)  # no tzinfo
        with pytest.raises(ValidationError, match="timezone-aware"):
            _make_event(created_at=naive_dt)


class TestGithubEventEquality:
    """Tests for identity-based equality semantics."""

    def test_same_event_id_is_equal(self) -> None:
        """Two events with the same event_id must be equal."""
        e1 = _make_event(event_id="same_id")
        e2 = _make_event(event_id="same_id", actor_login="different_user")
        assert e1 == e2

    def test_different_event_id_is_not_equal(self) -> None:
        """Two events with different event_ids must not be equal."""
        e1 = _make_event(event_id="id_1")
        e2 = _make_event(event_id="id_2")
        assert e1 != e2

    def test_event_is_hashable(self) -> None:
        """GithubEvent must be usable as a dict key / set member."""
        e = _make_event(event_id="hashable_id")
        event_set = {e}
        assert e in event_set


class TestGithubEventMethods:
    """Tests for domain behaviour methods."""

    def test_is_bot_event_returns_true_for_bot_login(self) -> None:
        """is_bot_event() must return True when actor_login ends with [bot]."""
        event = _make_event(actor_login="dependabot[bot]")
        assert event.is_bot_event() is True

    def test_is_bot_event_returns_false_for_human_login(self) -> None:
        """is_bot_event() must return False for a regular username."""
        event = _make_event(actor_login="linus_torvalds")
        assert event.is_bot_event() is False

    def test_event_date_returns_yyyy_mm_dd_string(self) -> None:
        """event_date() must return the UTC date in YYYY-MM-DD format."""
        event = _make_event(created_at=datetime(2024, 7, 4, 23, 59, 0, tzinfo=UTC))
        assert event.event_date() == "2024-07-04"

    def test_event_date_midnight_boundary_uses_utc(self) -> None:
        """event_date() at midnight UTC must return the correct UTC date."""
        event = _make_event(created_at=datetime(2024, 12, 31, 0, 0, 0, tzinfo=UTC))
        assert event.event_date() == "2024-12-31"

    def test_is_bot_event_with_github_actions_bot(self) -> None:
        """github-actions[bot] must be detected as a bot account."""
        event = _make_event(actor_login="github-actions[bot]")
        assert event.is_bot_event() is True

    def test_is_bot_event_with_renovate_bot(self) -> None:
        """renovate[bot] must be detected as a bot account."""
        event = _make_event(actor_login="renovate[bot]")
        assert event.is_bot_event() is True

    def test_is_bot_event_false_for_login_containing_bot_substring(self) -> None:
        """A login merely containing 'bot' in the middle must not be a bot."""
        event = _make_event(actor_login="robotics_dev")
        assert event.is_bot_event() is False

    def test_payload_defaults_to_empty_dict(self) -> None:
        """When payload is omitted, it must default to an empty dict."""
        event = GithubEvent(
            event_id="no_payload",
            event_type=EventType.PUSH,
            repo_id=RepositoryId.from_api(repo_id=1, repo_name="a/b"),
            actor_id=1,
            actor_login="dev",
            created_at=datetime(2024, 1, 1, tzinfo=UTC),
        )
        assert event.payload == {}

    def test_public_defaults_to_true(self) -> None:
        """When public is omitted, it must default to True."""
        event = GithubEvent(
            event_id="default_public",
            event_type=EventType.FORK,
            repo_id=RepositoryId.from_api(repo_id=1, repo_name="a/b"),
            actor_id=1,
            actor_login="dev",
            created_at=datetime(2024, 1, 1, tzinfo=UTC),
        )
        assert event.public is True
