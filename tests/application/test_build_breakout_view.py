"""Tests for breakout intelligence view construction."""

from __future__ import annotations

from datetime import UTC, datetime

from src.application.use_cases.build_breakout_view import BuildBreakoutViewUseCase


class FakeBreakoutReader:
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
                "repo_id": 1,
                "repo_full_name": "browser-use/browser-use",
                "repo_name": "browser-use",
                "html_url": "https://github.com/browser-use/browser-use",
                "description": "Browser agents.",
                "primary_language": "Python",
                "topics": ["agents", "browser"],
                "category": "Agent",
                "stargazers_count": 50_000,
                "watchers_count": 10_000,
                "forks_count": 2_000,
                "open_issues_count": 100,
                "subscribers_count": 700,
                "owner_login": "browser-use",
                "owner_avatar_url": "",
                "license_name": "MIT",
                "github_created_at": now,
                "github_pushed_at": now,
                "rank": 1,
                "star_count_in_window": 1200,
            }
        ][:limit]

    async def get_shock_movers(
        self,
        *,
        days: int,
        absolute_limit: int,
        percentage_limit: int,
        min_baseline_stars: int,
    ) -> dict[str, object]:
        del days, absolute_limit, percentage_limit, min_baseline_stars
        item = {
            "repo_full_name": "browser-use/browser-use",
            "previous_star_count_in_window": 300,
            "unique_actors_in_window": 240,
            "weekly_percent_gain": 12.5,
            "window_over_window_ratio": 4.0,
        }
        return {
            "absolute_movers": [item],
            "percentage_movers": [item],
        }


async def test_execute_returns_breakout_repository_with_scores_and_trace() -> None:
    use_case = BuildBreakoutViewUseCase(reader=FakeBreakoutReader())

    result = await use_case.execute(days=7, limit=5)

    assert len(result) == 1
    assert result[0].repo.repo_full_name == "browser-use/browser-use"
    assert result[0].breakout_score > 0
    assert result[0].durability_score > 0
    assert result[0].confidence_score > 0
    assert result[0].star_gain_vs_previous_window == 900
    assert "Star gain in last 7d" in result[0].explanation_trace[0]
