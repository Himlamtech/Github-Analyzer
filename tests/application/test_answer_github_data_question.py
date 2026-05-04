"""Unit tests for the grounded GitHub data chat agent."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from src.application.dtos.ai_chat_dto import AIChatMessageDTO
from src.application.dtos.ai_market_brief_dto import (
    MarketBreakoutRepoDTO,
    MarketBriefResponseDTO,
    MarketCategoryMoverDTO,
    MarketTopicShiftDTO,
)
from src.application.dtos.ai_repo_brief_dto import RepoBriefActivityDTO, RepoBriefResponseDTO
from src.application.dtos.ai_search_dto import (
    RepoSearchFiltersDTO,
    RepoSearchResponseDTO,
    RepoSearchResultDTO,
)
from src.application.dtos.repo_metadata_dto import RepoMetadataDTO
from src.application.use_cases.answer_github_data_question import (
    AnswerGithubDataQuestionUseCase,
)
from src.domain.exceptions import (
    AIInsightError,
    AISearchError,
    GenerationServiceError,
    ValidationError,
)

_NOW = datetime(2026, 3, 28, 12, 0, tzinfo=UTC)


class FakeMarketBriefUseCase:
    """Deterministic market tool boundary."""

    def __init__(self, response: MarketBriefResponseDTO) -> None:
        self._response = response
        self.calls: list[dict[str, object]] = []

    async def execute(self, **kwargs: object) -> MarketBriefResponseDTO:
        self.calls.append(kwargs)
        return self._response


class FailingMarketBriefUseCase:
    """Market tool boundary that simulates an unavailable data source."""

    async def execute(self, **kwargs: object) -> MarketBriefResponseDTO:
        raise AIInsightError("market context unavailable")


class FakeRepoBriefUseCase:
    """Deterministic repo brief tool boundary."""

    def __init__(self, response: RepoBriefResponseDTO) -> None:
        self._response = response
        self.calls: list[dict[str, object]] = []

    async def execute(self, **kwargs: object) -> RepoBriefResponseDTO:
        self.calls.append(kwargs)
        return self._response


class FailingRepoBriefUseCase:
    """Repo brief tool boundary that simulates an unavailable repo insight."""

    async def execute(self, **kwargs: object) -> RepoBriefResponseDTO:
        raise AIInsightError("repo context unavailable")


class FakeSearchUseCase:
    """Deterministic search tool boundary."""

    def __init__(self, response: RepoSearchResponseDTO) -> None:
        self._response = response
        self.calls: list[dict[str, object]] = []

    async def execute(self, **kwargs: object) -> RepoSearchResponseDTO:
        self.calls.append(kwargs)
        return self._response


class FailingSearchUseCase:
    """Search tool boundary that simulates an unavailable search backend."""

    async def execute(self, **kwargs: object) -> RepoSearchResponseDTO:
        raise AISearchError("search context unavailable")


class FakeGenerationService:
    """Structured generation boundary returning a fixed answer."""

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
    """Generation boundary that simulates an unavailable LLM."""

    async def generate_json(
        self,
        *,
        prompt: str,
        system_prompt: str,
        schema: dict[str, object],
    ) -> dict[str, object]:
        raise GenerationServiceError("ollama unavailable")


def _repo(repo_full_name: str, *, category: str = "Agent") -> RepoMetadataDTO:
    repo_name = repo_full_name.split("/")[-1]
    owner_login = repo_full_name.split("/")[0]
    return RepoMetadataDTO(
        repo_id=hash(repo_full_name) % 10_000,
        repo_full_name=repo_full_name,
        repo_name=repo_name,
        html_url=f"https://github.com/{repo_full_name}",
        description="Browser automation agents for GitHub AI trend analysis.",
        primary_language="Python",
        topics=["agent", "browser", "automation"],
        category=category,
        stargazers_count=52_000,
        watchers_count=52_000,
        forks_count=2_000,
        open_issues_count=80,
        subscribers_count=500,
        owner_login=owner_login,
        owner_avatar_url="",
        license_name="MIT",
        github_created_at=_NOW - timedelta(days=700),
        github_pushed_at=_NOW - timedelta(days=1),
        rank=1,
    )


def _market_response() -> MarketBriefResponseDTO:
    return MarketBriefResponseDTO(
        window_days=30,
        generated_at=_NOW,
        retrieval_mode="template",
        headline="Browser agents are leading the current GitHub AI cycle.",
        summary="Agent repos are absorbing fresh star velocity.",
        key_takeaways=["browser-use is the top breakout repo."],
        watchouts=["Momentum is concentrated in a narrow repo set."],
        breakout_repos=[
            MarketBreakoutRepoDTO(
                repo=_repo("browser-use/browser-use"),
                star_count_in_window=1_900,
                total_events_in_window=3_600,
                unique_actors_in_window=540,
                momentum_score=0.0365,
            )
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
            )
        ],
        topic_shifts=[
            MarketTopicShiftDTO(topic="browser", repo_count=5, star_count_in_window=2_300),
            MarketTopicShiftDTO(topic="agent", repo_count=12, star_count_in_window=4_600),
        ],
    )


def _repo_brief_response() -> RepoBriefResponseDTO:
    return RepoBriefResponseDTO(
        repo=_repo("browser-use/browser-use"),
        window_days=30,
        retrieval_mode="template",
        trend_verdict="accelerating",
        headline="browser-use/browser-use is accelerating.",
        summary="The repo combines strong adoption with fresh event velocity.",
        why_trending="Recent stars and issue traffic stepped up in the latest window.",
        star_count_in_window=1_900,
        total_events_in_window=3_600,
        unique_actors_in_window=540,
        latest_event_at=_NOW,
        activity_breakdown=[
            RepoBriefActivityDTO(event_type="WatchEvent", event_count=1_900),
            RepoBriefActivityDTO(event_type="IssuesEvent", event_count=900),
        ],
        key_signals=["Strong star intake."],
        watchouts=["Momentum is concentrated in WatchEvent activity."],
    )


def _search_response() -> RepoSearchResponseDTO:
    repo = _repo("browser-use/browser-use")
    return RepoSearchResponseDTO(
        query="browser automation agents",
        normalized_query="browser automation agents",
        retrieval_mode="lexical",
        total_candidates=8,
        returned_results=1,
        filters=RepoSearchFiltersDTO(
            category=None,
            primary_language=None,
            min_stars=500,
            days=30,
        ),
        results=[
            RepoSearchResultDTO(
                repo=repo,
                star_count_in_window=1_900,
                score=0.91,
                lexical_score=0.88,
                semantic_score=None,
                popularity_score=0.82,
                matched_terms=["browser", "agent"],
                why_matched=["Topic overlap: browser, agent."],
            )
        ],
    )


def _use_case(
    *,
    market: object | None = None,
    repo: object | None = None,
    search: object | None = None,
    generation: object | None = None,
    llm_enabled: bool = False,
) -> AnswerGithubDataQuestionUseCase:
    return AnswerGithubDataQuestionUseCase(
        market_brief_use_case=market or FakeMarketBriefUseCase(_market_response()),
        repo_brief_use_case=repo or FakeRepoBriefUseCase(_repo_brief_response()),
        search_use_case=search or FakeSearchUseCase(_search_response()),
        generation_service=generation,
        llm_enabled=llm_enabled,
    )


class TestAnswerGithubDataQuestionUseCase:
    async def test_execute_returns_model_answer_when_generation_succeeds(self) -> None:
        generation = FakeGenerationService(
            {
                "answer": "browser-use/browser-use is the strongest grounded signal.",
                "follow_up_questions": [
                    "Compare it with stagehand",
                    "Show related repos",
                ],
            }
        )
        use_case = _use_case(generation=generation, llm_enabled=True)

        result = await use_case.execute(
            question="Phan tich browser-use/browser-use",
            days=30,
            history=[],
        )

        assert result.mode == "model"
        assert result.intent == "repo"
        assert "repo-brief" in result.tools_used
        assert result.evidence
        assert generation.calls

    async def test_execute_falls_back_to_template_when_generation_fails(self) -> None:
        use_case = _use_case(generation=FailingGenerationService(), llm_enabled=True)

        result = await use_case.execute(
            question="Phan tich browser-use/browser-use",
            days=30,
            history=[],
        )

        assert result.mode == "template"
        assert "browser-use/browser-use" in result.answer
        assert "repo-brief" in result.tools_used

    async def test_execute_uses_market_data_when_search_and_repo_tools_fail(self) -> None:
        use_case = _use_case(
            repo=FailingRepoBriefUseCase(),
            search=FailingSearchUseCase(),
        )

        result = await use_case.execute(
            question="Repo nao dang tang sao nhanh nhat?",
            days=30,
            history=[],
        )

        assert result.mode == "template"
        assert result.tools_used == ["market-brief"]
        assert result.evidence[0].source == "/ai/market-brief.breakout_repos"

    async def test_execute_uses_history_repo_when_question_omits_repo_name(self) -> None:
        repo_tool = FakeRepoBriefUseCase(_repo_brief_response())
        use_case = _use_case(repo=repo_tool)

        result = await use_case.execute(
            question="Phan tich tiep no",
            days=30,
            history=[
                AIChatMessageDTO(
                    role="user",
                    content="Truoc do toi hoi ve browser-use/browser-use",
                )
            ],
        )

        assert result.intent == "repo"
        assert repo_tool.calls[0]["repo_name"] == "browser-use/browser-use"

    async def test_execute_raises_controlled_error_when_all_tools_fail(self) -> None:
        use_case = _use_case(
            market=FailingMarketBriefUseCase(),
            repo=FailingRepoBriefUseCase(),
            search=FailingSearchUseCase(),
        )

        with pytest.raises(AIInsightError, match="No GitHub trend data"):
            await use_case.execute(question="Repo nao dang hot?", days=30, history=[])

    async def test_execute_rejects_blank_question_before_calling_tools(self) -> None:
        market_tool = FakeMarketBriefUseCase(_market_response())
        use_case = _use_case(market=market_tool)

        with pytest.raises(ValidationError, match="at least 2 characters"):
            await use_case.execute(question=" ", days=30, history=[])

        assert market_tool.calls == []
