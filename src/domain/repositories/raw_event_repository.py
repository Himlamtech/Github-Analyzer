"""Abstract repository interface for raw event batch storage.

Designed for the Parquet archive tier: append-only, partition-aware,
and optimised for large sequential writes rather than random access.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date


class RawEventRepositoryABC(ABC):
    """Port (interface) for writing and reading raw event batches.

    The concrete implementation lives in Infrastructure
    (``parquet_repository.py``).  The Domain layer defines only the
    contract; it has zero knowledge of Parquet or Spark.
    """

    @abstractmethod
    async def append_batch(
        self,
        records: list[dict[str, object]],
        event_date: date,
        event_type: str,
    ) -> int:
        """Append a batch of raw event records to the archive partition.

        Args:
            records:    List of serialisable event dictionaries.
            event_date: Hive partition key — determines the date folder.
            event_type: Hive partition key — determines the event_type folder.

        Returns:
            Number of records successfully written.
        """

    @abstractmethod
    async def read_partition(
        self,
        event_date: date,
        event_type: str | None = None,
    ) -> list[dict[str, object]]:
        """Read all records from a specific date (and optionally type) partition.

        Args:
            event_date:  The date partition to read.
            event_type:  If provided, restrict to this event type partition.
                         If ``None``, return all event types for the date.

        Returns:
            List of raw event dictionaries from the Parquet archive.
        """
