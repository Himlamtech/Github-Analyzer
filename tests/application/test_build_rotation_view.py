"""Tests for ecosystem rotation intelligence view construction."""

from __future__ import annotations

from datetime import UTC, datetime

from src.application.use_cases.build_rotation_view import BuildRotationViewUseCase


class FakeRotationReader:
    async def get_topic_rotation(self, *, days: int, limit: int) -> list[dict[str, object]]:
        del days
        return [
            {
                "topic": "agentic-frameworks",
                "current_star_count": 600,
                "previous_star_count": 120,
                "star_delta": 480,
                "repo_count": 14,
                "rank": 1,
            }
        ][:limit]

    async def get_top_repos(
        self,
        category: str | None,
        days: int,
        limit: int,
    ) -> list[dict[str, object]]:
        del category, days
        now = datetime(2026, 4, 1, 12, 0, tzinfo=UTC)
        return [
            {
                "repo_full_name": "browser-use/browser-use",
                "topics": ["agentic-frameworks", "agents"],
                "github_created_at": now,
                "github_pushed_at": now,
            }
        ][:limit]


async def test_execute_returns_rotation_category_with_drivers_and_top_repos() -> None:
    use_case = BuildRotationViewUseCase(reader=FakeRotationReader())

    result = await use_case.execute(days=7, limit=5)

    assert len(result) == 1
    assert result[0].category == "Agentic Frameworks"
    assert result[0].repo_count == 14
    assert result[0].top_repos == ["browser-use/browser-use"]
    assert result[0].confidence_score > 0
    assert result[0].rotation_drivers
