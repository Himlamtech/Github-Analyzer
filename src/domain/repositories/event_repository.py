"""Abstract repository interface for GithubEvent persistence.

Defined in the Domain layer so the Application layer can depend on
this abstraction without any knowledge of ClickHouse, Parquet, or any
other concrete storage technology.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import date

    from src.domain.entities.github_event import GithubEvent
    from src.domain.value_objects.repository_id import RepositoryId


class EventRepositoryABC(ABC):
    """Port (interface) for persisting and querying GithubEvent aggregates.

    Infrastructure layer provides a concrete implementation backed by
    ClickHouse.  The Application layer depends only on this ABC.
    """

    @abstractmethod
    async def save(self, event: GithubEvent) -> None:
        """Persist a single GithubEvent.

        Args:
            event: The aggregate to store.
        """

    @abstractmethod
    async def save_batch(self, events: list[GithubEvent]) -> None:
        """Persist a batch of GithubEvent aggregates atomically.

        Prefer bulk inserts over looping ``save()`` for throughput.

        Args:
            events: List of aggregates to store.
        """

    @abstractmethod
    async def find_by_repo(self, repo_id: RepositoryId, limit: int = 100) -> list[GithubEvent]:
        """Return events for a specific repository, most recent first.

        Args:
            repo_id: The target repository identity.
            limit:   Maximum number of events to return.

        Returns:
            Ordered list of matching GithubEvent instances.
        """

    @abstractmethod
    async def find_by_date_range(
        self,
        start: date,
        end: date,
        limit: int = 1000,
    ) -> list[GithubEvent]:
        """Return events whose ``created_at`` falls within [start, end].

        Args:
            start:  Inclusive lower bound (UTC date).
            end:    Inclusive upper bound (UTC date).
            limit:  Maximum number of events to return.

        Returns:
            Ordered list of matching GithubEvent instances.
        """

    @abstractmethod
    async def get_max_created_at(self) -> float | None:
        """Return the Unix timestamp of the most recent stored event.

        Used to compute the data-freshness Prometheus gauge.

        Returns:
            Unix epoch float, or ``None`` if no events are stored yet.
        """
