"""HTTP reader for official RSS and Atom news feeds."""

from __future__ import annotations

from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
import xml.etree.ElementTree as ET

import httpx

from src.domain.entities.external_news_item import ExternalNewsItem
from src.domain.exceptions import ExternalSourceError

_ATOM_NAMESPACE = {"atom": "http://www.w3.org/2005/Atom"}


class RssNewsReader:
    """Fetch and parse official RSS or Atom feeds."""

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(connect=5.0, read=8.0, write=10.0, pool=5.0),
            follow_redirects=True,
            headers={"User-Agent": "github-analyzer-news-preview/0.1"},
        )

    async def aclose(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    async def fetch_latest(
        self,
        *,
        provider: str,
        url: str,
        source_type: str,
        limit: int,
    ) -> list[ExternalNewsItem]:
        response = await self._client.get(url)
        if not response.is_success:
            raise ExternalSourceError(
                f"External source {provider} returned HTTP {response.status_code}."
            )

        try:
            root = ET.fromstring(response.text)
        except ET.ParseError as exc:
            raise ExternalSourceError(
                f"External source {provider} returned invalid XML content."
            ) from exc

        normalized_type = source_type.lower()
        if normalized_type == "atom":
            return self._parse_atom(
                provider=provider,
                entries=root.findall("atom:entry", _ATOM_NAMESPACE),
                limit=limit,
            )
        if normalized_type == "rss":
            channel = root.find("channel")
            items = [] if channel is None else channel.findall("item")
            return self._parse_rss(provider=provider, items=items, limit=limit)

        raise ExternalSourceError(f"Unsupported external source type: {source_type!r}.")

    @staticmethod
    def _parse_datetime(value: str | None) -> datetime:
        if not value:
            return datetime.now(tz=UTC)
        try:
            parsed = parsedate_to_datetime(value)
        except (TypeError, ValueError):
            try:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                return datetime.now(tz=UTC)
        return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)

    def _parse_rss(
        self,
        *,
        provider: str,
        items: list[ET.Element],
        limit: int,
    ) -> list[ExternalNewsItem]:
        parsed_items: list[ExternalNewsItem] = []
        for item in items[:limit]:
            title = (item.findtext("title") or "Untitled").strip()
            link = (item.findtext("link") or "").strip()
            guid = (item.findtext("guid") or link or title).strip()
            description = (item.findtext("description") or "").strip()
            published_at = self._parse_datetime(item.findtext("pubDate"))
            parsed_items.append(
                ExternalNewsItem(
                    source_id=guid,
                    provider=provider,
                    title=title,
                    url=link,
                    published_at=published_at,
                    summary=description,
                )
            )
        return parsed_items

    def _parse_atom(
        self,
        *,
        provider: str,
        entries: list[ET.Element],
        limit: int,
    ) -> list[ExternalNewsItem]:
        parsed_items: list[ExternalNewsItem] = []
        for entry in entries[:limit]:
            title = (
                entry.findtext(
                    "atom:title",
                    default="Untitled",
                    namespaces=_ATOM_NAMESPACE,
                )
                or "Untitled"
            ).strip()
            link_element = entry.find("atom:link", _ATOM_NAMESPACE)
            link = "" if link_element is None else (link_element.attrib.get("href") or "").strip()
            source_id = (
                entry.findtext("atom:id", default=link or title, namespaces=_ATOM_NAMESPACE)
                or link
                or title
            ).strip()
            summary = (
                entry.findtext("atom:summary", default="", namespaces=_ATOM_NAMESPACE)
                or entry.findtext("atom:content", default="", namespaces=_ATOM_NAMESPACE)
                or ""
            ).strip()
            published_at = self._parse_datetime(
                entry.findtext("atom:published", namespaces=_ATOM_NAMESPACE)
                or entry.findtext("atom:updated", namespaces=_ATOM_NAMESPACE)
            )
            parsed_items.append(
                ExternalNewsItem(
                    source_id=source_id,
                    provider=provider,
                    title=title,
                    url=link,
                    published_at=published_at,
                    summary=summary,
                )
            )
        return parsed_items
