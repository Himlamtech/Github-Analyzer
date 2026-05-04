"""EventType value object — enumeration of supported GitHub event types.

Only the five event types relevant to AI trend analysis are modeled.
Unknown types received from the API raise InvalidEventTypeError so that
unrecognised data never silently flows downstream.
"""

from __future__ import annotations

from enum import StrEnum

from src.domain.exceptions import InvalidEventTypeError


class EventType(StrEnum):
    """Enumeration of GitHub event types tracked by this system.

    Inherits from ``str`` so that instances serialise directly to their
    string value without extra unwrapping in JSON serializers.
    """

    WATCH = "WatchEvent"
    FORK = "ForkEvent"
    PUSH = "PushEvent"
    CREATE = "CreateEvent"
    ISSUES = "IssuesEvent"

    @classmethod
    def from_raw(cls, raw: str) -> EventType:
        """Parse a raw GitHub event type string into an EventType enum value.

        Args:
            raw: The ``type`` field value from a GitHub API event object.

        Returns:
            The matching EventType enum member.

        Raises:
            InvalidEventTypeError: If ``raw`` does not match any known type.
        """
        try:
            return cls(raw)
        except ValueError as exc:
            raise InvalidEventTypeError(
                f"Unknown GitHub event type: {raw!r}. Supported types: {[e.value for e in cls]}"
            ) from exc

    def __str__(self) -> str:
        return self.value
