"""Backward-compatible no-op news adapter.

This module intentionally keeps the legacy import path alive while removing the
runtime dependency on SearXNG. Existing callers receive an empty headline list.
"""

from __future__ import annotations


class SearXNGNewsService:
    """Compatibility adapter that disables external news lookups."""

    def __init__(
        self,
        *,
        base_url: str,
        timeout_seconds: float,
        headline_limit: int,
    ) -> None:
        self._base_url = base_url
        self._timeout_seconds = timeout_seconds
        self._headline_limit = headline_limit

    async def search_repo_news(
        self,
        *,
        repo_full_name: str,
        days: int,
    ) -> list[dict[str, str | None]]:
        """Return no headlines.

        Args:
            repo_full_name: Repository identifier in owner/name format.
            days: Lookback window kept for call compatibility.

        Returns:
            An empty list because external news fetching is disabled.
        """
        _ = (repo_full_name, days)
        return []
