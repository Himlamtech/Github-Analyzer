"""GithubEvent — the core Aggregate Root for this system.

Identity is determined by ``event_id`` (the string ID assigned by GitHub).
All business invariants related to an event are enforced here, keeping the
Application and Infrastructure layers free of domain logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from src.domain.exceptions import ValidationError

if TYPE_CHECKING:
    from datetime import datetime

    from src.domain.value_objects.event_type import EventType
    from src.domain.value_objects.repository_id import RepositoryId


@dataclass
class GithubEvent:
    """Aggregate Root representing a single GitHub public event.

    An event is uniquely identified by ``event_id``.  Two ``GithubEvent``
    instances with the same ``event_id`` are considered equal regardless of
    any other attribute values.

    Attributes:
        event_id:   GitHub-assigned unique event identifier (string).
        event_type: Typed enumeration of the event category.
        repo_id:    Value object encapsulating the repository identity.
        actor_id:   GitHub user/organisation ID who triggered the event.
        actor_login:GitHub username of the actor.
        created_at: UTC timestamp when the event was created.
        payload:    Raw payload dict from the GitHub API (type-specific).
        public:     Whether the event is visible to the public.
    """

    event_id: str
    event_type: EventType
    repo_id: RepositoryId
    actor_id: int
    actor_login: str
    created_at: datetime
    payload: dict[str, object] = field(default_factory=dict)
    public: bool = True

    def __post_init__(self) -> None:
        self._validate()

    def _validate(self) -> None:
        """Enforce all invariants on the aggregate.

        Raises:
            ValidationError: If any invariant is violated.
        """
        if not self.event_id or not self.event_id.strip():
            raise ValidationError("event_id must be a non-empty string.")
        if self.actor_id <= 0:
            raise ValidationError(f"actor_id must be a positive integer, got {self.actor_id!r}.")
        if not self.actor_login or not self.actor_login.strip():
            raise ValidationError("actor_login must be a non-empty string.")
        if self.created_at.tzinfo is None:
            raise ValidationError(
                "created_at must be timezone-aware (UTC). "
                f"Got naive datetime: {self.created_at!r}."
            )

    def is_bot_event(self) -> bool:
        """Return True if the actor appears to be an automated bot account.

        Bot detection is based on the ``[bot]`` suffix convention used by
        GitHub Apps and the GitHub Actions bot.
        """
        return self.actor_login.endswith("[bot]")

    def event_date(self) -> str:
        """Return the event date as a ``YYYY-MM-DD`` string (UTC).

        Used as a Hive-style partition key in the Parquet archive.
        """
        return self.created_at.strftime("%Y-%m-%d")

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, GithubEvent):
            return NotImplemented
        return self.event_id == other.event_id

    def __hash__(self) -> int:
        return hash(self.event_id)

    def __repr__(self) -> str:
        return (
            f"GithubEvent(id={self.event_id!r}, type={self.event_type}, "
            f"repo={self.repo_id}, actor={self.actor_login!r})"
        )
