"""Abstract repository interface for persisted external news intelligence data."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime

    from src.domain.entities.external_news_item import ExternalNewsItem


class ExternalNewsRepositoryABC(ABC):
    """Port for storing and reading official external news items and source health."""

    @abstractmethod
    async def upsert_items(self, items: list[ExternalNewsItem]) -> int:
        """Persist or replace external news items by stable source ID."""

    @abstractmethod
    async def append_source_health_snapshot(
        self,
        *,
        provider: str,
        source_url: str,
        status: str,
        fetched_count: int,
        error_message: str | None,
        checked_at: datetime,
    ) -> None:
        """Append an operational source-health snapshot for a fetch attempt."""

    @abstractmethod
    async def list_latest_items(
        self,
        *,
        provider: str | None,
        limit: int,
    ) -> list[dict[str, object]]:
        """Return latest persisted external news items."""

    @abstractmethod
    async def list_latest_source_health(self) -> list[dict[str, object]]:
        """Return the latest source-health snapshot per provider/url."""
