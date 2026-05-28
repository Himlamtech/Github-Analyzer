"""Unit tests for grounded repository brief generation."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest

from src.application.dtos.ai_repo_brief_dto import (
    RepoBriefActivityDTO,
    RepoBriefContextDTO,
    RepoBriefTimeseriesPointDTO,
)
from src.application.dtos.repo_metadata_dto import RepoMetadataDTO
from src.application.use_cases.generate_repo_brief import GenerateRepoBriefUseCase
from src.domain.exceptions import RepoInsightNotFoundError

_NOW = datetime(2026, 3, 28, 12, 0, tzinfo=UTC)


class FakeContextProvider:
    """Deterministic storage boundary for repo brief context."""

    def __init__(self, context: RepoBriefContextDTO) -> None:
        self._context = context
        self.calls: list[dict[str, object]] = []

    async def get_repo_brief_context(
        self,
        *,
        repo_name: str,
        days: int,
    ) -> RepoBriefContextDTO:
        self.calls.append({"repo_name": repo_name, "days": days})
        return self._context


class MissingContextProvider:
    """Storage boundary that simulates an unknown repository."""

    async def get_repo_brief_context(
        self,
        *,
        repo_name: str,
        days: int,
    ) -> RepoBriefContextDTO:
        raise RepoInsightNotFoundError(f"Repository not found: {repo_name}")


def _context() -> RepoBriefContextDTO:
    repo = RepoMetadataDTO(
        repo_id=1,
        repo_full_name="browser-use/browser-use",
        repo_name="browser-use",
        html_url="https://github.com/browser-use/browser-use",
        description="Browser automation agents for web workflows.",
        primary_language="Python",
        topics=["agent", "browser", "automation"],
        category="Agent",
        stargazers_count=52_000,
        watchers_count=52_000,
        forks_count=2_000,
        open_issues_count=80,
        subscribers_count=500,
        owner_login="browser-use",
        owner_avatar_url="",
        license_name="MIT",
        github_created_at=_NOW - timedelta(days=700),
        github_pushed_at=_NOW - timedelta(days=4),
        rank=1,
    )
    return RepoBriefContextDTO(
        repo=repo,
        window_days=30,
        star_count_in_window=1_900,
        total_events_in_window=3_600,
        unique_actors_in_window=540,
        latest_event_at=_NOW,
        activity_breakdown=[
            RepoBriefActivityDTO(event_type="WatchEvent", event_count=1_900),
            RepoBriefActivityDTO(event_type="IssuesEvent", event_count=900),
            RepoBriefActivityDTO(event_type="ForkEvent", event_count=400),
        ],
        timeseries=[
            RepoBriefTimeseriesPointDTO(
                event_date=date(2026, 3, 1),
                star_count=20,
                total_events=70,
            ),
            RepoBriefTimeseriesPointDTO(
                event_date=date(2026, 3, 8),
                star_count=35,
                total_events=90,
            ),
            RepoBriefTimeseriesPointDTO(
                event_date=date(2026, 3, 15),
                star_count=60,
                total_events=120,
            ),
            RepoBriefTimeseriesPointDTO(
                event_date=date(2026, 3, 22),
                star_count=95,
                total_events=180,
            ),
        ],
    )


class TestGenerateRepoBriefUseCase:
    async def test_execute_returns_template_brief(self) -> None:
        provider = FakeContextProvider(_context())
        use_case = GenerateRepoBriefUseCase(provider)

        result = await use_case.execute(repo_name="browser-use/browser-use", days=30)

        assert result.retrieval_mode == "template"
        assert result.trend_verdict in {"accelerating", "steady", "emerging", "quiet"}
        assert any("total GitHub stars" in signal for signal in result.key_signals)
        assert result.watchouts
        assert provider.calls[0]["repo_name"] == "browser-use/browser-use"

    async def test_execute_propagates_missing_repository(self) -> None:
        use_case = GenerateRepoBriefUseCase(MissingContextProvider())

        with pytest.raises(RepoInsightNotFoundError, match="Repository not found"):
            await use_case.execute(repo_name="missing/repo", days=30)
