"""Tests for the computed framework radar snapshot use case."""

from __future__ import annotations

from src.application.use_cases.get_framework_radar_snapshot import (
    GetFrameworkRadarSnapshotUseCase,
)


class FakeFrameworkRadarReader:
    async def get_top_repos(
        self,
        category: str | None,
        days: int,
        limit: int,
    ) -> list[dict[str, object]]:
        del category, days, limit
        return [
            {
                "repo_full_name": "langchain-ai/langchain",
                "description": "Framework for LLM applications and agents.",
                "topics": ["langchain", "agents", "llm"],
                "stargazers_count": 110_000,
                "open_issues_count": 120,
                "star_count_in_window": 700,
            }
        ]

    async def get_trending(self, days: int, limit: int) -> list[dict[str, object]]:
        del days, limit
        return [
            {
                "repo_full_name": "langchain-ai/langchain",
                "description": "Framework for LLM applications and agents.",
                "topics": ["langchain", "agents", "llm"],
                "stargazers_count": 110_000,
                "open_issues_count": 120,
                "star_count_in_window": 700,
            }
        ]


async def test_execute_returns_framework_radar_snapshot() -> None:
    use_case = GetFrameworkRadarSnapshotUseCase(reader=FakeFrameworkRadarReader())

    result = await use_case.execute()

    assert result.frameworks
    assert result.frameworks[0].framework_id == "langchain"
    assert result.frameworks[0].velocity_score >= 0.0
    assert result.frameworks[0].matched_repo_count == 1
    assert result.frameworks[0].representative_repos == ["langchain-ai/langchain"]
    assert result.winners
    assert result.warnings
