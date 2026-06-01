"""Abstract reader interface for official external news sources."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.domain.entities.external_news_item import ExternalNewsItem


class ExternalNewsReaderABC(ABC):
    """Port for reading official external news items from configured sources."""

    @abstractmethod
    async def fetch_latest(
        self,
        *,
        provider: str,
        url: str,
        source_type: str,
        limit: int,
    ) -> list[ExternalNewsItem]:
        """Return the latest official items from a configured source."""
