"""Unit tests for the EventType value object."""

from __future__ import annotations

import pytest

from src.domain.exceptions import InvalidEventTypeError
from src.domain.value_objects.event_type import EventType


class TestEventTypeFromRaw:
    """Tests for EventType.from_raw() parsing."""

    def test_parse_watch_event_succeeds(self) -> None:
        """Happy path: 'WatchEvent' parses to EventType.WATCH."""
        et = EventType.from_raw("WatchEvent")
        assert et == EventType.WATCH

    def test_parse_fork_event_succeeds(self) -> None:
        """Happy path: 'ForkEvent' parses to EventType.FORK."""
        assert EventType.from_raw("ForkEvent") == EventType.FORK

    def test_parse_push_event_succeeds(self) -> None:
        """Happy path: 'PushEvent' parses to EventType.PUSH."""
        assert EventType.from_raw("PushEvent") == EventType.PUSH

    def test_parse_create_event_succeeds(self) -> None:
        """Happy path: 'CreateEvent' parses to EventType.CREATE."""
        assert EventType.from_raw("CreateEvent") == EventType.CREATE

    def test_parse_issues_event_succeeds(self) -> None:
        """Happy path: 'IssuesEvent' parses to EventType.ISSUES."""
        assert EventType.from_raw("IssuesEvent") == EventType.ISSUES

    def test_parse_unknown_type_raises_invalid_event_type_error(self) -> None:
        """Error path: unknown type string must raise InvalidEventTypeError."""
        with pytest.raises(InvalidEventTypeError, match="Unknown GitHub event type"):
            EventType.from_raw("DeleteEvent")

    def test_parse_empty_string_raises_invalid_event_type_error(self) -> None:
        """Edge case: empty string must raise InvalidEventTypeError."""
        with pytest.raises(InvalidEventTypeError):
            EventType.from_raw("")

    def test_event_type_str_returns_raw_string(self) -> None:
        """EventType.__str__ must return the raw string value."""
        assert str(EventType.WATCH) == "WatchEvent"

    def test_event_type_is_str_subclass(self) -> None:
        """EventType must be directly usable as a string for JSON serialisation."""
        et = EventType.FORK
        assert isinstance(et, str)
        assert et == "ForkEvent"
