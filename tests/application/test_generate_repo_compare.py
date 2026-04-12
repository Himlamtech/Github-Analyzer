"""Unit tests for grounded repository comparison generation."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest

from university.github.src.application.dtos.ai_repo_brief_dto import (
    RepoBriefActivityDTO,
    RepoBriefContextDTO,
    RepoBriefTimeseriesPointDTO,
)
from university.github.src.application.dtos.repo_metadata_dto import RepoMetadataDTO
from university.github.src.application.use_cases.generate_repo_compare import GenerateRepoCompareUseCase
from university.github.src.domain.exceptions import (
    GenerationServiceError,
    RepoInsightNotFoundError,
    ValidationError,
)

_NOW = datetime(2026, 3, 28, 12, 0, tzinfo=UTC)


class FakeContextProvider:
    """Deterministic storage boundary for comparison context."""

    def __init__(self, contexts: dict[str, RepoBriefContextDTO]) -> None:
        self._contexts = contexts
        self.calls: list[dict[str, object]] = []

    async def get_repo_brief_context(
        self,
        *,
        repo_name: str,
        days: int,
    ) -> RepoBriefContextDTO:
        self.calls.append({"repo_name": repo_name, "days": days})
        if repo_name not in self._contexts:
            raise RepoInsightNotFoundError(f"Repository not found: {repo_name}")
        return self._contexts[repo_name]


class FakeGenerationService:
    """Structured generation boundary returning a fixed payload."""

    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload
        self.calls: list[dict[str, object]] = []

    async def generate_json(
        self,
        *,
        prompt: str,
        system_prompt: str,
        schema: dict[str, object],
    ) -> dict[str, object]:
        self.calls.append(
            {
                "prompt": prompt,
                "system_prompt": system_prompt,
                "schema": schema,
            }
        )
        return dict(self._payload)


class FailingGenerationService:
    """Generation boundary that simulates a runtime failure."""

    async def generate_json(
        self,
        *,
        prompt: str,
        system_prompt: str,
        schema: dict[str, object],
    ) -> dict[str, object]:
        raise GenerationServiceError("model unavailable")


def _context(
    repo_full_name: str,
    *,
    category: str,
    stars: int,
    window_stars: int,
    events: int,
    actors: int,
    forks: int,
) -> RepoBriefContextDTO:
    repo_name = repo_full_name.split("/")[-1]
    owner_login = repo_full_name.split("/")[0]
    repo = RepoMetadataDTO(
        repo_id=hash(repo_full_name) % 1000,
        repo_full_name=repo_full_name,
        repo_name=repo_name,
        html_url=f"https://github.com/{repo_full_name}",
        description=f"{repo_name} repository description.",
        primary_language="Python",
        topics=[category.lower(), "ai"],
        category=category,
        stargazers_count=stars,
        watchers_count=stars,
        forks_count=forks,
        open_issues_count=60,
        subscribers_count=400,
        owner_login=owner_login,
        owner_avatar_url="",
        license_name="MIT",
        github_created_at=_NOW - timedelta(days=700),
        github_pushed_at=_NOW - timedelta(days=4),
        rank=1,
    )
    return RepoBriefContextDTO(
        repo=repo,
        window_days=30,
        star_count_in_window=window_stars,
        total_events_in_window=events,
        unique_actors_in_window=actors,
        latest_event_at=_NOW,
        activity_breakdown=[
            RepoBriefActivityDTO(event_type="WatchEvent", event_count=window_stars),
            RepoBriefActivityDTO(event_type="IssuesEvent", event_count=max(events // 4, 1)),
        ],
        timeseries=[
            RepoBriefTimeseriesPointDTO(
                event_date=date(2026, 3, 1),
                star_count=max(window_stars // 4, 1),
                total_events=max(events // 4, 1),
            ),
            RepoBriefTimeseriesPointDTO(
                event_date=date(2026, 3, 8),
                star_count=max(window_stars // 3, 1),
                total_events=max(events // 3, 1),
            ),
            RepoBriefTimeseriesPointDTO(
                event_date=date(2026, 3, 15),
                star_count=max(window_stars // 2, 1),
                total_events=max(events // 2, 1),
            ),
        ],
    )


class TestGenerateRepoCompareUseCase:
    async def test_execute_returns_model_compare_when_generation_succeeds(self) -> None:
        provider = FakeContextProvider(
            {
                "browser-use/browser-use": _context(
                    "browser-use/browser-use",
                    category="Agent",
                    stars=52_000,
                    window_stars=1_900,
                    events=3_600,
                    actors=540,
                    forks=2_000,
                ),
                "langchain-ai/langchain": _context(
                    "langchain-ai/langchain",
                    category="Agent",
                    stars=104_000,
                    window_stars=800,
                    events=2_100,
                    actors=320,
                    forks=12_000,
                ),
            }
        )
        generation_service = FakeGenerationService(
            {
                "headline": "browser-use/browser-use is stronger on current momentum.",
                "summary": (
                    "browser-use has the sharper near-term growth signal, while "
                    "langchain leads on installed base."
                ),
                "overall_winner": "base",
                "key_differences": ["browser-use leads on recent stars."],
                "when_to_choose_base": ["Choose it for fast-moving browser agents."],
                "when_to_choose_compare": ["Choose it for a broader framework ecosystem."],
            }
        )
        use_case = GenerateRepoCompareUseCase(
            provider,
            generation_service=generation_service,
            llm_enabled=True,
        )

        result = await use_case.execute(
            base_repo_name="browser-use/browser-use",
            compare_repo_name="langchain-ai/langchain",
            days=30,
        )

        assert result.retrieval_mode == "model"
        assert result.overall_winner == "base"
        assert generation_service.calls

    async def test_execute_falls_back_to_template_when_generation_fails(self) -> None:
        provider = FakeContextProvider(
            {
                "browser-use/browser-use": _context(
                    "browser-use/browser-use",
                    category="Agent",
                    stars=52_000,
                    window_stars=1_900,
                    events=3_600,
                    actors=540,
                    forks=2_000,
                ),
                "langchain-ai/langchain": _context(
                    "langchain-ai/langchain",
                    category="Agent",
                    stars=104_000,
                    window_stars=800,
                    events=2_100,
                    actors=320,
                    forks=12_000,
                ),
            }
        )
        use_case = GenerateRepoCompareUseCase(
            provider,
            generation_service=FailingGenerationService(),
            llm_enabled=True,
        )

        result = await use_case.execute(
            base_repo_name="browser-use/browser-use",
            compare_repo_name="langchain-ai/langchain",
            days=30,
        )

        assert result.retrieval_mode == "template"
        assert result.metric_snapshot
        assert result.key_differences

    async def test_execute_rejects_same_repository(self) -> None:
        provider = FakeContextProvider({})
        use_case = GenerateRepoCompareUseCase(
            provider,
            generation_service=None,
            llm_enabled=False,
        )

        with pytest.raises(ValidationError, match="two distinct repositories"):
            await use_case.execute(
                base_repo_name="browser-use/browser-use",
                compare_repo_name="browser-use/browser-use",
                days=30,
            )
