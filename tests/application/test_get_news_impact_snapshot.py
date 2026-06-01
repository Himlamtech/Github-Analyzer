"""Tests for the computed news impact use case."""

from __future__ import annotations

from datetime import UTC, datetime

from src.application.use_cases.get_news_impact_snapshot import GetNewsImpactSnapshotUseCase
from src.domain.exceptions import DashboardQueryError


class FakeExternalNewsRepository:
    async def list_latest_items(
        self,
        *,
        provider: str | None,
        limit: int,
        include_quarantined: bool = False,
    ) -> list[dict[str, object]]:
        del provider, limit, include_quarantined
        return [
            {
                "source_id": "openai-preview-1",
                "provider": "OpenAI",
                "title": "OpenAI browser agent launch",
                "url": "https://example.com/preview-1",
                "published_at": datetime(2026, 3, 30, 9, 0, tzinfo=UTC),
                "summary": "Official preview summary for browser automation agents.",
                "source_type": "rss",
                "event_type": "launch",
                "linked_entities": ["OpenAI", "Browser Use"],
                "linked_categories": ["Coding Agents & Automation"],
                "linked_repo_full_names": ["browser-use/browser-use"],
                "linked_framework_ids": ["browser-use", "openai-agents"],
                "quality_score": 90.0,
                "is_quarantined": False,
                "quarantine_reason": None,
            }
        ]

    async def get_item_by_source_id(self, source_id: str) -> dict[str, object] | None:
        rows = await self.list_latest_items(provider=None, limit=10)
        for row in rows:
            if row["source_id"] == source_id:
                return row
        return None


class FakeDashboardReader:
    async def get_top_repos(
        self,
        category: str | None,
        days: int,
        limit: int,
    ) -> list[dict[str, object]]:
        del category, days, limit
        return [
            {
                "repo_full_name": "browser-use/browser-use",
                "description": "Browser agents for operator workflows.",
                "category": "Coding Agents & Automation",
                "topics": ["browser-use", "agents"],
                "star_count_in_window": 1200,
            }
        ]

    async def get_trending(self, days: int, limit: int) -> list[dict[str, object]]:
        del days, limit
        return [
            {
                "repo_full_name": "browser-use/browser-use",
                "description": "Browser agents for operator workflows.",
                "category": "Coding Agents & Automation",
                "topics": ["browser-use", "agents"],
                "star_count_in_window": 1200,
            }
        ]


async def test_execute_returns_computed_news_impact_snapshot() -> None:
    use_case = GetNewsImpactSnapshotUseCase(
        repository=FakeExternalNewsRepository(),
        reader=FakeDashboardReader(),
    )

    result = await use_case.execute()

    assert len(result) == 1
    assert result[0].event_id == "openai-preview-1"
    assert result[0].source == "persisted_external_news"
    assert result[0].impact_curve
    assert result[0].top_impacted_repos == ["browser-use/browser-use"]
    assert result[0].linked_repos == ["browser-use/browser-use"]
    assert result[0].linked_frameworks == ["browser-use", "openai-agents"]
    assert result[0].explanation_trace


async def test_get_detail_returns_single_event() -> None:
    use_case = GetNewsImpactSnapshotUseCase(
        repository=FakeExternalNewsRepository(),
        reader=FakeDashboardReader(),
    )

    result = await use_case.get_detail("openai-preview-1")

    assert result is not None
    assert result.event_id == "openai-preview-1"
    assert result.quality_score == 90.0


class FailingDashboardReader:
    async def get_top_repos(
        self,
        category: str | None,
        days: int,
        limit: int,
    ) -> list[dict[str, object]]:
        del category, days, limit
        raise DashboardQueryError("repo metadata history query failed")

    async def get_trending(self, days: int, limit: int) -> list[dict[str, object]]:
        del days, limit
        raise DashboardQueryError("trending query failed")


async def test_execute_returns_events_when_dashboard_telemetry_is_unavailable() -> None:
    use_case = GetNewsImpactSnapshotUseCase(
        repository=FakeExternalNewsRepository(),
        reader=FailingDashboardReader(),
    )

    result = await use_case.execute()

    assert len(result) == 1
    assert result[0].event_id == "openai-preview-1"
    assert result[0].top_impacted_repos == ["browser-use/browser-use"]
    assert any("temporarily degraded" in item for item in result[0].explanation_trace)
