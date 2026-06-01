"""ExternalNewsItem entity for official launch and news source ingestion."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime


@dataclass(frozen=True, slots=True)
class ExternalNewsItem:
    """Single external news item fetched from an official source feed."""

    source_id: str
    provider: str
    title: str
    url: str
    published_at: datetime
    summary: str
