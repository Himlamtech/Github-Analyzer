"""Unit tests for grounded AI market brief generation."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from src.application.dtos.ai_market_brief_dto import (
    MarketBreakoutRepoDTO,
    MarketBriefContextDTO,
    MarketCategoryMoverDTO,
    MarketTopicShiftDTO,
)
from src.application.dtos.repo_metadata_dto import RepoMetadataDTO
from src.application.use_cases.build_market_brief import BuildMarketBriefUseCase
from src.domain.exceptions import GenerationServiceError

_NOW = datetime(2026, 3, 28, 12, 0, tzinfo=UTC)


class FakeContextProvider:
    """Deterministic storage boundary for market context."""

    def __init__(self, context: MarketBriefContextDTO) -> None:
        self._context = context
        self.calls: list[dict[str, object]] = []

    async def get_market_brief_context(
        self,
        *,
        days: int,
        breakout_limit: int,
        category_limit: int,
        topic_limit: int,
    ) -> MarketBriefContextDTO:
        self.calls.append(
            {
                "days": days,
                "breakout_limit": breakout_limit,
                "category_limit": category_limit,
                "topic_limit": topic_limit,
            }
        )
        return self._context


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


def _repo(repo_full_name: str, *, stars: int, category: str, topics: list[str]) -> RepoMetadataDTO:
    repo_name = repo_full_name.split("/")[-1]
    owner_login = repo_full_name.split("/")[0]
    return RepoMetadataDTO(
        repo_id=hash(repo_full_name) % 1000,
        repo_full_name=repo_full_name,
        repo_name=repo_name,
        html_url=f"https://github.com/{repo_full_name}",
        description=f"{repo_name} repository description.",
        primary_language="Python",
        topics=topics,
        category=category,
        stargazers_count=stars,
        watchers_count=stars,
        forks_count=max(stars // 20, 1),
        open_issues_count=40,
        subscribers_count=200,
        owner_login=owner_login,
        owner_avatar_url="",
        license_name="MIT",
        github_created_at=_NOW - timedelta(days=400),
        github_pushed_at=_NOW - timedelta(days=1),
        rank=1,
    )


def _context() -> MarketBriefContextDTO:
    return MarketBriefContextDTO(
        window_days=30,
        generated_at=_NOW,
        breakout_repos=[
            MarketBreakoutRepoDTO(
                repo=_repo(
                    "browser-use/browser-use",
                    stars=52_000,
                    category="Agent",
                    topics=["agent", "browser"],
                ),
                star_count_in_window=1_900,
                total_events_in_window=3_600,
                unique_actors_in_window=540,
                momentum_score=0.0365,
            ),
            MarketBreakoutRepoDTO(
                repo=_repo(
                    "browserbase/stagehand",
                    stars=26_000,
                    category="Agent",
                    topics=["agent", "browser", "automation"],
                ),
                star_count_in_window=1_100,
                total_events_in_window=2_400,
                unique_actors_in_window=310,
                momentum_score=0.0423,
            ),
        ],
        category_movers=[
            MarketCategoryMoverDTO(
                category="Agent",
                active_repo_count=16,
                total_stars_in_window=4_200,
                total_events_in_window=7_800,
                leader_repo_name="browser-use/browser-use",
                leader_stars_in_window=1_900,
                share_of_window_stars=0.58,
            ),
            MarketCategoryMoverDTO(
                category="LLM",
                active_repo_count=11,
                total_stars_in_window=2_100,
                total_events_in_window=4_600,
                leader_repo_name="langchain-ai/langchain",
                leader_stars_in_window=900,
                share_of_window_stars=0.29,
            ),
        ],
        topic_shifts=[
            MarketTopicShiftDTO(topic="browser", repo_count=5, star_count_in_window=2_300),
            MarketTopicShiftDTO(topic="agent", repo_count=12, star_count_in_window=4_600),
        ],
    )


class TestBuildMarketBriefUseCase:
    async def test_execute_returns_model_brief_when_generation_succeeds(self) -> None:
        provider = FakeContextProvider(_context())
        generation_service = FakeGenerationService(
            {
                "headline": "Browser agents are leading the current GitHub AI cycle.",
                "summary": (
                    "browser-use and stagehand are concentrating fresh attention while "
                    "Agent remains the strongest category."
                ),
                "key_takeaways": [
                    "browser-use is the top breakout repo.",
                    "Agent leads category star flow.",
                    "Browser is the fastest-moving topic cluster.",
                ],
                "watchouts": ["Attention is concentrated in a narrow slice of repos."],
            }
        )
        use_case = BuildMarketBriefUseCase(
            provider,
            generation_service=generation_service,
            llm_enabled=True,
        )

        result = await use_case.execute(
            days=30,
            breakout_limit=5,
            category_limit=4,
            topic_limit=6,
        )

        assert result.retrieval_mode == "model"
        assert result.headline == "Browser agents are leading the current GitHub AI cycle."
        assert provider.calls == [
            {
                "days": 30,
                "breakout_limit": 5,
                "category_limit": 4,
                "topic_limit": 6,
            }
        ]
        assert generation_service.calls

    async def test_execute_falls_back_to_template_when_generation_fails(self) -> None:
        provider = FakeContextProvider(_context())
        use_case = BuildMarketBriefUseCase(
            provider,
            generation_service=FailingGenerationService(),
            llm_enabled=True,
        )

        result = await use_case.execute(
            days=30,
            breakout_limit=5,
            category_limit=4,
            topic_limit=6,
        )

        assert result.retrieval_mode == "template"
        assert "browser-use/browser-use" in result.headline
        assert result.breakout_repos[0].repo.repo_full_name == "browser-use/browser-use"
        assert result.category_movers[0].category == "Agent"

    async def test_execute_llm_disabled_uses_template_mode(self) -> None:
        """When llm_enabled=False, use case must skip generation and fall back to template."""
        provider = FakeContextProvider(_context())
        generation_service = FakeGenerationService(
            {
                "headline": "Should not be called",
                "summary": "Should not be called",
                "key_takeaways": [],
                "watchouts": [],
            }
        )
        use_case = BuildMarketBriefUseCase(
            provider,
            generation_service=generation_service,
            llm_enabled=False,
        )

        result = await use_case.execute(
            days=7,
            breakout_limit=3,
            category_limit=2,
            topic_limit=3,
        )

        assert result.retrieval_mode == "template"
        assert len(generation_service.calls) == 0

    async def test_execute_passes_correct_parameters_to_context_provider(self) -> None:
        """Use case must forward all execution arguments to the context provider."""
        provider = FakeContextProvider(_context())
        use_case = BuildMarketBriefUseCase(
            provider,
            generation_service=FailingGenerationService(),
            llm_enabled=False,
        )

        await use_case.execute(
            days=14,
            breakout_limit=10,
            category_limit=5,
            topic_limit=8,
        )

        assert provider.calls == [
            {
                "days": 14,
                "breakout_limit": 10,
                "category_limit": 5,
                "topic_limit": 8,
            }
        ]
