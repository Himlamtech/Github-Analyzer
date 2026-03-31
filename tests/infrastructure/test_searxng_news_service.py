"""Unit tests for the SearXNG-backed news lookup adapter."""

from __future__ import annotations

from httpx import Response
import pytest
import respx

from src.domain.exceptions import DashboardQueryError
from src.infrastructure.news.searxng_news_service import SearXNGNewsService


@pytest.mark.asyncio
@respx.mock
async def test_search_repo_news_normalizes_headlines() -> None:
    service = SearXNGNewsService(
        base_url="http://searxng:8080",
        timeout_seconds=5.0,
        headline_limit=2,
    )
    route = respx.get("http://searxng:8080/search").mock(
        return_value=Response(
            200,
            json={
                "results": [
                    {
                        "title": "Browser Use explodes on GitHub",
                        "url": "https://example.com/browser-use",
                        "content": "The repo gained attention this week.",
                        "engine": "google news",
                    },
                    {
                        "title": "A second headline",
                        "url": "https://example.com/second",
                        "content": "Coverage continues.",
                        "source": "Example News",
                    },
                ]
            },
        )
    )

    result = await service.search_repo_news(repo_full_name="browser-use/browser-use", days=7)

    assert route.called
    assert result == [
        {
            "title": "Browser Use explodes on GitHub",
            "url": "https://example.com/browser-use",
            "source": "google news",
            "snippet": "The repo gained attention this week.",
            "engine": "google news",
        },
        {
            "title": "A second headline",
            "url": "https://example.com/second",
            "source": "Example News",
            "snippet": "Coverage continues.",
            "engine": None,
        },
    ]


@pytest.mark.asyncio
@respx.mock
async def test_search_repo_news_raises_on_invalid_payload() -> None:
    service = SearXNGNewsService(
        base_url="http://searxng:8080",
        timeout_seconds=5.0,
        headline_limit=2,
    )
    respx.get("http://searxng:8080/search").mock(return_value=Response(200, json={"foo": "bar"}))

    with pytest.raises(DashboardQueryError, match="invalid payload"):
        await service.search_repo_news(repo_full_name="browser-use/browser-use", days=7)
