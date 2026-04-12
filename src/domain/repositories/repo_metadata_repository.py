"""Abstract repository interface for RepoMetadata persistence.

Infrastructure layer provides the ClickHouse implementation.
The Application layer depends only on this ABC.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.domain.value_objects.repo_category import RepoCategory
    from src.domain.value_objects.repo_metadata import RepoMetadata


class RepoMetadataRepositoryABC(ABC):
    """Port for persisting and querying RepoMetadata snapshots.

    All methods are asynchronous.  Infrastructure implementations wrap
    synchronous drivers (e.g., clickhouse-driver) in ``asyncio.to_thread``.
    """

    @abstractmethod
    async def upsert_batch(self, repos: list[RepoMetadata]) -> None:
        """Insert or replace a batch of RepoMetadata records.

        Uses ReplacingMergeTree semantics: rows with the same repo_full_name
        and a higher refreshed_at value replace older rows on background merge.

        Args:
            repos: List of RepoMetadata value objects to upsert.
        """

    @abstractmethod
    async def append_history_batch(
        self,
        repos: list[RepoMetadata],
        snapshot_source: str,
    ) -> None:
        """Append one history snapshot row per repository fetch.

        Args:
            repos: List of RepoMetadata value objects to append to history.
            snapshot_source: Logical source name for the snapshot batch.
        """

    @abstractmethod
    async def get_top_by_category(
        self,
        category: RepoCategory,
        days: int,
        limit: int,
    ) -> list[dict[str, object]]:
        """Return top repos in a category ranked by recent star velocity.

        Joins repo_metadata with repo_star_counts to compute star delta
        over the last N days.

        Args:
            category: Filter to this category only.
            days:     Look-back window in days for star velocity.
            limit:    Maximum rows to return.

        Returns:
            List of dicts with repo metadata + ``star_count_in_window`` key,
            ordered by star_count_in_window descending.
        """

    @abstractmethod
    async def get_trending(self, days: int, limit: int) -> list[dict[str, object]]:
        """Return trending repos by star growth velocity across all categories.

        Args:
            days:  Look-back window in days.
            limit: Maximum rows to return.

        Returns:
            List of dicts with repo metadata + ``star_count_in_window`` key,
            ordered by star_count_in_window descending.
        """

    @abstractmethod
    async def get_category_summary(self) -> list[dict[str, object]]:
        """Return per-category aggregate stats.

        Returns:
            List of dicts with keys:
            ``category``, ``repo_count``, ``total_stars``,
            ``top_repo_name``, ``top_repo_stars``, ``weekly_star_delta``.
        """
