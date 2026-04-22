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


class TestEventTypeEnumCompleteness:
    """Tests verifying the full set of supported event types."""

    def test_exactly_five_event_types_are_defined(self) -> None:
        """Only five event types are supported by this system."""
        assert len(EventType) == 5

    def test_all_event_types_are_str_instances(self) -> None:
        """Every EventType member must be a str for transparent serialisation."""
        for et in EventType:
            assert isinstance(et, str)

    def test_event_type_values_end_with_event_suffix(self) -> None:
        """All event type string values must end with 'Event'."""
        for et in EventType:
            assert et.value.endswith("Event"), f"{et.value!r} does not end with 'Event'"

    def test_from_raw_case_sensitive_rejection(self) -> None:
        """from_raw must reject lowercase and mixed-case variants."""
        from src.domain.exceptions import InvalidEventTypeError

        with pytest.raises(InvalidEventTypeError):
            EventType.from_raw("watchevent")

        with pytest.raises(InvalidEventTypeError):
            EventType.from_raw("WATCHEVENT")

    def test_event_type_is_hashable(self) -> None:
        """EventType values must be usable in sets and as dict keys."""
        seen = {et for et in EventType}
        assert len(seen) == 5
