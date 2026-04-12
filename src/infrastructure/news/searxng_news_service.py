"""SearXNG-backed news lookup for breakout repository storytelling."""

from __future__ import annotations

from typing import Any

import httpx

from src.domain.exceptions import DashboardQueryError


class SearXNGNewsService:
    """Fetch external headlines for repositories via SearXNG's HTTP API."""

    def __init__(
        self,
        *,
        base_url: str,
        timeout_seconds: float,
        headline_limit: int,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._headline_limit = headline_limit

    async def search_repo_news(
        self,
        *,
        repo_full_name: str,
        days: int,
    ) -> list[dict[str, str | None]]:
        """Return normalized external headlines for one repository."""
        query = f'"{repo_full_name}" GitHub'
        params = {
            "q": query,
            "categories": "news,general",
            "format": "json",
            "time_range": _time_range(days),
        }
        url = f"{self._base_url}/search"

        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise DashboardQueryError(f"SearXNG news lookup failed: {exc}") from exc

        body = response.json()
        results = body.get("results")
        if not isinstance(results, list):
            raise DashboardQueryError("SearXNG news lookup returned an invalid payload.")

        normalized: list[dict[str, str | None]] = []
        for item in results:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or "").strip()
            item_url = str(item.get("url") or "").strip()
            if not title or not item_url:
                continue
            normalized.append(
                {
                    "title": title,
                    "url": item_url,
                    "source": _coerce_source(item),
                    "snippet": str(item.get("content") or item.get("snippet") or "").strip(),
                    "engine": _optional_text(item.get("engine")),
                }
            )
            if len(normalized) >= self._headline_limit:
                break

        return normalized


def _coerce_source(item: dict[str, Any]) -> str:
    source = item.get("source")
    if isinstance(source, str) and source.strip():
        return source.strip()
    parsed_url = _optional_text(item.get("parsed_url"))
    if parsed_url is not None:
        return parsed_url
    engine = _optional_text(item.get("engine"))
    return engine or "web"


def _optional_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned or None


def _time_range(days: int) -> str:
    if days <= 7:
        return "day"
    if days <= 31:
        return "month"
    return "year"
