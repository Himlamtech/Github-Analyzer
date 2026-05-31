"""Repository category value object.

The application no longer performs topic-specific classification. Repository
metadata is retained for analytics, and all repositories are assigned the
single neutral fallback category.
"""

from __future__ import annotations

from enum import StrEnum


class RepoCategory(StrEnum):
    """Neutral repository category taxonomy."""

    OTHER = "Other"

    def __str__(self) -> str:
        return self.value
