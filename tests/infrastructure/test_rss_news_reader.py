"""Tests for the RSS and Atom external news reader."""

from __future__ import annotations

from datetime import UTC

import respx

from src.infrastructure.external_sources.rss_news_reader import RssNewsReader


@respx.mock
async def test_fetch_latest_parses_rss_feed() -> None:
    respx.get("https://example.com/rss.xml").respond(
        200,
        text="""
        <rss version="2.0">
          <channel>
            <item>
              <title>OpenAI launch</title>
              <link>https://example.com/openai-launch</link>
              <guid>openai-launch-1</guid>
              <description>Launch summary</description>
              <pubDate>Mon, 01 Jan 2026 12:00:00 GMT</pubDate>
            </item>
          </channel>
        </rss>
        """,
    )

    reader = RssNewsReader()
    try:
        items = await reader.fetch_latest(
            provider="OpenAI",
            url="https://example.com/rss.xml",
            source_type="rss",
            limit=3,
        )
    finally:
        await reader.aclose()

    assert len(items) == 1
    assert items[0].source_id == "openai-launch-1"
    assert items[0].published_at.tzinfo == UTC


@respx.mock
async def test_fetch_latest_parses_atom_feed() -> None:
    respx.get("https://example.com/atom.xml").respond(
        200,
        text="""
        <feed xmlns="http://www.w3.org/2005/Atom">
          <entry>
            <id>tag:example.com,2026:1</id>
            <title>Anthropic release</title>
            <link href="https://example.com/anthropic-release" />
            <updated>2026-01-01T12:00:00Z</updated>
            <summary>Release summary</summary>
          </entry>
        </feed>
        """,
    )

    reader = RssNewsReader()
    try:
        items = await reader.fetch_latest(
            provider="Anthropic",
            url="https://example.com/atom.xml",
            source_type="atom",
            limit=2,
        )
    finally:
        await reader.aclose()

    assert len(items) == 1
    assert items[0].title == "Anthropic release"
    assert items[0].url == "https://example.com/anthropic-release"
