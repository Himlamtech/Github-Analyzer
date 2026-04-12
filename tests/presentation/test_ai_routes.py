"""Presentation tests for the AI repository search API router."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from unittest.mock import patch

from fastapi.testclient import TestClient
import pytest

from university.github.src.application.dtos.ai_market_brief_dto import (
    MarketBreakoutRepoDTO,
    MarketBriefResponseDTO,
    MarketCategoryMoverDTO,
    MarketTopicShiftDTO,
)
from university.github.src.application.dtos.ai_related_repo_dto import (
    RelatedRepoResultDTO,
    RelatedReposResponseDTO,
)
from university.github.src.application.dtos.ai_repo_brief_dto import (
    RepoBriefActivityDTO,
    RepoBriefResponseDTO,
)
from university.github.src.application.dtos.ai_repo_compare_dto import (
    RepoCompareMetricDTO,
    RepoCompareResponseDTO,
)
from university.github.src.application.dtos.ai_search_dto import (
    RepoSearchFiltersDTO,
    RepoSearchResponseDTO,
    RepoSearchResultDTO,
)
from university.github.src.application.dtos.repo_metadata_dto import RepoMetadataDTO
from university.github.src.domain.exceptions import AIInsightError, AISearchError, RepoInsightNotFoundError
from university.github.src.infrastructure.config import get_settings
from university.github.src.presentation.api.ai_routes import (
    _get_market_brief_use_case,
    _get_related_repos_use_case,
    _get_repo_brief_use_case,
    _get_repo_compare_use_case,
    _get_search_use_case,
)
from university.github.src.presentation.api.routes import app

if TYPE_CHECKING:
    from collections.abc import Iterator

_NOW = datetime(2026, 3, 28, 12, 0, tzinfo=UTC)


class FakeSearchUseCase:
    """Simple async stub that returns a fixed response."""

    def __init__(self, response: RepoSearchResponseDTO) -> None:
        self._response = response
        self.received: dict[str, object] | None = None

    async def execute(self, **kwargs: object) -> RepoSearchResponseDTO:
        self.received = kwargs
        return self._response


class FailingSearchUseCase:
    """Async stub that simulates a storage/runtime failure."""

    async def execute(self, **kwargs: object) -> RepoSearchResponseDTO:
        raise AISearchError("candidate query failed")


class FakeMarketBriefUseCase:
    """Simple async stub that returns a fixed market brief."""

    def __init__(self, response: MarketBriefResponseDTO) -> None:
        self._response = response
        self.received: dict[str, object] | None = None

    async def execute(self, **kwargs: object) -> MarketBriefResponseDTO:
        self.received = kwargs
        return self._response


class FailingMarketBriefUseCase:
    """Async stub that simulates a market brief runtime failure."""

    async def execute(self, **kwargs: object) -> MarketBriefResponseDTO:
        raise AIInsightError("query failed")


class FakeRepoBriefUseCase:
    """Simple async stub that returns a fixed repo brief."""

    def __init__(self, response: RepoBriefResponseDTO) -> None:
        self._response = response
        self.received: dict[str, object] | None = None

    async def execute(self, **kwargs: object) -> RepoBriefResponseDTO:
        self.received = kwargs
        return self._response


class MissingRepoBriefUseCase:
    """Async stub that simulates a missing repository."""

    async def execute(self, **kwargs: object) -> RepoBriefResponseDTO:
        raise RepoInsightNotFoundError("Repository not found")


class FailingRepoBriefUseCase:
    """Async stub that simulates a repo brief runtime failure."""

    async def execute(self, **kwargs: object) -> RepoBriefResponseDTO:
        raise AIInsightError("query failed")


class FakeRepoCompareUseCase:
    """Simple async stub that returns a fixed repo comparison."""

    def __init__(self, response: RepoCompareResponseDTO) -> None:
        self._response = response
        self.received: dict[str, object] | None = None

    async def execute(self, **kwargs: object) -> RepoCompareResponseDTO:
        self.received = kwargs
        return self._response


class FailingRepoCompareUseCase:
    """Async stub that simulates a repo compare runtime failure."""

    async def execute(self, **kwargs: object) -> RepoCompareResponseDTO:
        raise AIInsightError("query failed")


class FakeRelatedReposUseCase:
    """Simple async stub that returns related repositories."""

    def __init__(self, response: RelatedReposResponseDTO) -> None:
        self._response = response
        self.received: dict[str, object] | None = None

    async def execute(self, **kwargs: object) -> RelatedReposResponseDTO:
        self.received = kwargs
        return self._response


class FailingRelatedReposUseCase:
    """Async stub that simulates a related-repos runtime failure."""

    async def execute(self, **kwargs: object) -> RelatedReposResponseDTO:
        raise AIInsightError("query failed")


class MissingRelatedReposUseCase:
    """Async stub that simulates a missing source repository."""

    async def execute(self, **kwargs: object) -> RelatedReposResponseDTO:
        raise RepoInsightNotFoundError("Repository not found")


def _build_response() -> RepoSearchResponseDTO:
    repo = RepoMetadataDTO(
        repo_id=1,
        repo_full_name="browser-use/browser-use",
        repo_name="browser-use",
        html_url="https://github.com/browser-use/browser-use",
        description="Browser automation agents.",
        primary_language="Python",
        topics=["agent", "browser"],
        category="Agent",
        stargazers_count=52_000,
        watchers_count=52_000,
        forks_count=2_000,
        open_issues_count=50,
        subscribers_count=400,
        owner_login="browser-use",
        owner_avatar_url="",
        license_name="MIT",
        github_created_at=_NOW,
        github_pushed_at=_NOW,
        rank=1,
    )
    return RepoSearchResponseDTO(
        query="browser agents",
        normalized_query="browser agents",
        retrieval_mode="hybrid",
        total_candidates=12,
        returned_results=1,
        filters=RepoSearchFiltersDTO(
            category="Agent",
            primary_language="Python",
            min_stars=10_000,
            days=30,
        ),
        results=[
            RepoSearchResultDTO(
                repo=repo,
                star_count_in_window=1_800,
                score=0.91,
                lexical_score=0.88,
                semantic_score=0.93,
                popularity_score=0.82,
                matched_terms=["browser", "agent"],
                why_matched=["Topic overlap: browser, agent."],
            )
        ],
    )


def _build_market_brief_response() -> MarketBriefResponseDTO:
    repo = RepoMetadataDTO(
        repo_id=1,
        repo_full_name="browser-use/browser-use",
        repo_name="browser-use",
        html_url="https://github.com/browser-use/browser-use",
        description="Browser automation agents.",
        primary_language="Python",
        topics=["agent", "browser"],
        category="Agent",
        stargazers_count=52_000,
        watchers_count=52_000,
        forks_count=2_000,
        open_issues_count=50,
        subscribers_count=400,
        owner_login="browser-use",
        owner_avatar_url="",
        license_name="MIT",
        github_created_at=_NOW,
        github_pushed_at=_NOW,
        rank=1,
    )
    return MarketBriefResponseDTO(
        window_days=30,
        generated_at=_NOW,
        retrieval_mode="model",
        headline="Browser agents are leading the current GitHub AI cycle.",
        summary=(
            "Agent is the strongest category while browser automation repos absorb "
            "the sharpest attention."
        ),
        key_takeaways=[
            "browser-use is the top breakout repo.",
            "Agent leads category star flow.",
            "browser is the fastest-moving topic cluster.",
        ],
        watchouts=["Attention is concentrated in a narrow slice of repos."],
        breakout_repos=[
            MarketBreakoutRepoDTO(
                repo=repo,
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
            MarketTopicShiftDTO(topic="browser", repo_count=5, star_count_in_window=2_300)
        ],
    )


def _build_repo_brief_response() -> RepoBriefResponseDTO:
    repo = RepoMetadataDTO(
        repo_id=1,
        repo_full_name="browser-use/browser-use",
        repo_name="browser-use",
        html_url="https://github.com/browser-use/browser-use",
        description="Browser automation agents.",
        primary_language="Python",
        topics=["agent", "browser"],
        category="Agent",
        stargazers_count=52_000,
        watchers_count=52_000,
        forks_count=2_000,
        open_issues_count=50,
        subscribers_count=400,
        owner_login="browser-use",
        owner_avatar_url="",
        license_name="MIT",
        github_created_at=_NOW,
        github_pushed_at=_NOW,
        rank=1,
    )
    return RepoBriefResponseDTO(
        repo=repo,
        window_days=30,
        retrieval_mode="model",
        trend_verdict="accelerating",
        headline="browser-use/browser-use is accelerating in agent tooling.",
        summary="The repo combines large existing adoption with strong fresh event velocity.",
        why_trending="Recent star and issue activity both stepped up in the last 30 days.",
        star_count_in_window=1_800,
        total_events_in_window=3_200,
        unique_actors_in_window=500,
        latest_event_at=_NOW,
        activity_breakdown=[
            RepoBriefActivityDTO(event_type="WatchEvent", event_count=1800),
            RepoBriefActivityDTO(event_type="IssuesEvent", event_count=700),
        ],
        key_signals=["Strong recent star intake."],
        watchouts=["Momentum is still concentrated in a few event types."],
    )


def _build_repo_compare_response() -> RepoCompareResponseDTO:
    base_repo = RepoMetadataDTO(
        repo_id=1,
        repo_full_name="browser-use/browser-use",
        repo_name="browser-use",
        html_url="https://github.com/browser-use/browser-use",
        description="Browser automation agents.",
        primary_language="Python",
        topics=["agent", "browser"],
        category="Agent",
        stargazers_count=52_000,
        watchers_count=52_000,
        forks_count=2_000,
        open_issues_count=50,
        subscribers_count=400,
        owner_login="browser-use",
        owner_avatar_url="",
        license_name="MIT",
        github_created_at=_NOW,
        github_pushed_at=_NOW,
        rank=1,
    )
    compare_repo = RepoMetadataDTO(
        repo_id=2,
        repo_full_name="langchain-ai/langchain",
        repo_name="langchain",
        html_url="https://github.com/langchain-ai/langchain",
        description="Framework for LLM apps.",
        primary_language="Python",
        topics=["agent", "llm"],
        category="Agent",
        stargazers_count=104_000,
        watchers_count=104_000,
        forks_count=12_000,
        open_issues_count=200,
        subscribers_count=800,
        owner_login="langchain-ai",
        owner_avatar_url="",
        license_name="MIT",
        github_created_at=_NOW,
        github_pushed_at=_NOW,
        rank=2,
    )
    return RepoCompareResponseDTO(
        base_repo=base_repo,
        compare_repo=compare_repo,
        window_days=30,
        retrieval_mode="model",
        overall_winner="base",
        headline="browser-use/browser-use is stronger on current momentum.",
        summary="browser-use leads on recent adoption while langchain wins on installed base.",
        key_differences=["browser-use leads on recent stars."],
        when_to_choose_base=["Choose it for fast-moving browser agents."],
        when_to_choose_compare=["Choose it for a broader framework ecosystem."],
        metric_snapshot=[
            RepoCompareMetricDTO(
                key="window_stars",
                label="Stars (30d)",
                base_value=1800,
                compare_value=800,
                winner="base",
            )
        ],
    )


def _build_related_repos_response() -> RelatedReposResponseDTO:
    source_repo = RepoMetadataDTO(
        repo_id=1,
        repo_full_name="browser-use/browser-use",
        repo_name="browser-use",
        html_url="https://github.com/browser-use/browser-use",
        description="Browser automation agents.",
        primary_language="Python",
        topics=["agent", "browser"],
        category="Agent",
        stargazers_count=52_000,
        watchers_count=52_000,
        forks_count=2_000,
        open_issues_count=50,
        subscribers_count=400,
        owner_login="browser-use",
        owner_avatar_url="",
        license_name="MIT",
        github_created_at=_NOW,
        github_pushed_at=_NOW,
        rank=1,
    )
    related_repo = RepoMetadataDTO(
        repo_id=3,
        repo_full_name="browserbase/stagehand",
        repo_name="stagehand",
        html_url="https://github.com/browserbase/stagehand",
        description="Browser automation framework.",
        primary_language="Python",
        topics=["agent", "browser", "automation"],
        category="Agent",
        stargazers_count=26_000,
        watchers_count=26_000,
        forks_count=1_200,
        open_issues_count=40,
        subscribers_count=200,
        owner_login="browserbase",
        owner_avatar_url="",
        license_name="MIT",
        github_created_at=_NOW,
        github_pushed_at=_NOW,
        rank=3,
    )
    return RelatedReposResponseDTO(
        source_repo=source_repo,
        total_candidates=12,
        returned_results=1,
        results=[
            RelatedRepoResultDTO(
                repo=related_repo,
                similarity_score=0.81,
                star_count_in_window=1100,
                shared_topics=["agent", "browser", "automation"],
                why_related=["Shared topics: agent, browser, automation."],
            )
        ],
    )


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("GITHUB_API_TOKENS", "test-token")
    monkeypatch.setenv("CLICKHOUSE_PASSWORD", "test-password")
    get_settings.cache_clear()
    with (
        patch("src.presentation.api.routes.start_metrics_server", return_value=None),
        patch("src.presentation.api.routes.setup_tracing", return_value=None),
        patch("src.presentation.api.routes.shutdown_tracing", return_value=None),
        patch(
            "src.infrastructure.storage.clickhouse_repo_observation_bootstrap."
            "ClickHouseRepoObservationBootstrapService.execute",
            return_value=None,
        ),
        TestClient(app) as test_client,
    ):
        yield test_client
    app.dependency_overrides.clear()
    get_settings.cache_clear()


class TestAIRoutes:
    def test_health_response_exposes_trace_headers(self, client: TestClient) -> None:
        trace_id = "0123456789abcdef0123456789abcdef"

        with patch("src.presentation.api.routes.get_current_trace_id", return_value=trace_id):
            response = client.get("/health", headers={"Origin": "http://localhost:3000"})

        assert response.status_code == 200
        assert response.headers["X-Request-Id"]
        assert response.headers["X-Trace-Id"] == trace_id
        assert trace_id in response.headers["X-Trace-Explore-Url"]
        assert "tempo_ds" in response.headers["X-Trace-Explore-Url"]
        assert (
            response.headers["access-control-expose-headers"]
            == "X-Request-Id, X-Trace-Id, X-Trace-Explore-Url"
        )

    def test_search_returns_response_payload(self, client: TestClient) -> None:
        fake_use_case = FakeSearchUseCase(_build_response())
        app.dependency_overrides[_get_search_use_case] = lambda: fake_use_case

        response = client.get(
            "/ai/search",
            params={
                "query": "browser agents",
                "category": "Agent",
                "language": "Python",
                "days": 30,
                "limit": 5,
            },
        )

        assert response.status_code == 200
        assert response.json()["retrieval_mode"] == "hybrid"
        assert fake_use_case.received == {
            "query": "browser agents",
            "category": "Agent",
            "primary_language": "Python",
            "min_stars": 10000,
            "days": 30,
            "limit": 5,
        }

    def test_search_returns_503_on_ai_search_failure(self, client: TestClient) -> None:
        app.dependency_overrides[_get_search_use_case] = lambda: FailingSearchUseCase()

        response = client.get("/ai/search", params={"query": "browser agents"})

        assert response.status_code == 503
        assert response.json()["detail"] == "AI search unavailable"

    def test_market_brief_returns_response_payload(self, client: TestClient) -> None:
        fake_use_case = FakeMarketBriefUseCase(_build_market_brief_response())
        app.dependency_overrides[_get_market_brief_use_case] = lambda: fake_use_case

        response = client.get(
            "/ai/market-brief",
            params={
                "days": 30,
                "breakout_limit": 5,
                "category_limit": 4,
                "topic_limit": 6,
            },
        )

        assert response.status_code == 200
        assert response.json()["retrieval_mode"] == "model"
        assert fake_use_case.received == {
            "days": 30,
            "breakout_limit": 5,
            "category_limit": 4,
            "topic_limit": 6,
        }

    def test_market_brief_returns_503_on_runtime_failure(self, client: TestClient) -> None:
        app.dependency_overrides[_get_market_brief_use_case] = lambda: FailingMarketBriefUseCase()

        response = client.get("/ai/market-brief", params={"days": 30})

        assert response.status_code == 503
        assert response.json()["detail"] == "AI market brief unavailable"

    def test_repo_brief_returns_response_payload(self, client: TestClient) -> None:
        fake_use_case = FakeRepoBriefUseCase(_build_repo_brief_response())
        app.dependency_overrides[_get_repo_brief_use_case] = lambda: fake_use_case

        response = client.get(
            "/ai/repo-brief",
            params={"repo_name": "browser-use/browser-use", "days": 30},
        )

        assert response.status_code == 200
        assert response.json()["trend_verdict"] == "accelerating"
        assert fake_use_case.received == {
            "repo_name": "browser-use/browser-use",
            "days": 30,
        }

    def test_repo_brief_returns_404_when_repo_missing(self, client: TestClient) -> None:
        app.dependency_overrides[_get_repo_brief_use_case] = lambda: MissingRepoBriefUseCase()

        response = client.get(
            "/ai/repo-brief",
            params={"repo_name": "missing/repo", "days": 30},
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "Repository not found"

    def test_repo_brief_returns_503_on_runtime_failure(self, client: TestClient) -> None:
        app.dependency_overrides[_get_repo_brief_use_case] = lambda: FailingRepoBriefUseCase()

        response = client.get(
            "/ai/repo-brief",
            params={"repo_name": "browser-use/browser-use", "days": 30},
        )

        assert response.status_code == 503
        assert response.json()["detail"] == "AI repo brief unavailable"

    def test_repo_compare_returns_response_payload(self, client: TestClient) -> None:
        fake_use_case = FakeRepoCompareUseCase(_build_repo_compare_response())
        app.dependency_overrides[_get_repo_compare_use_case] = lambda: fake_use_case

        response = client.get(
            "/ai/repo-compare",
            params={
                "base_repo_name": "browser-use/browser-use",
                "compare_repo_name": "langchain-ai/langchain",
                "days": 30,
            },
        )

        assert response.status_code == 200
        assert response.json()["overall_winner"] == "base"
        assert fake_use_case.received == {
            "base_repo_name": "browser-use/browser-use",
            "compare_repo_name": "langchain-ai/langchain",
            "days": 30,
        }

    def test_repo_compare_returns_503_on_runtime_failure(self, client: TestClient) -> None:
        app.dependency_overrides[_get_repo_compare_use_case] = lambda: FailingRepoCompareUseCase()

        response = client.get(
            "/ai/repo-compare",
            params={
                "base_repo_name": "browser-use/browser-use",
                "compare_repo_name": "langchain-ai/langchain",
            },
        )

        assert response.status_code == 503
        assert response.json()["detail"] == "AI repo compare unavailable"

    def test_related_repos_returns_response_payload(self, client: TestClient) -> None:
        fake_use_case = FakeRelatedReposUseCase(_build_related_repos_response())
        app.dependency_overrides[_get_related_repos_use_case] = lambda: fake_use_case

        response = client.get(
            "/ai/related-repos",
            params={"repo_name": "browser-use/browser-use", "days": 30, "limit": 6},
        )

        assert response.status_code == 200
        assert response.json()["returned_results"] == 1
        assert fake_use_case.received == {
            "repo_name": "browser-use/browser-use",
            "days": 30,
            "limit": 6,
        }

    def test_related_repos_returns_503_on_runtime_failure(self, client: TestClient) -> None:
        app.dependency_overrides[_get_related_repos_use_case] = lambda: (
            FailingRelatedReposUseCase()
        )

        response = client.get(
            "/ai/related-repos",
            params={"repo_name": "browser-use/browser-use", "days": 30},
        )

        assert response.status_code == 503
        assert response.json()["detail"] == "AI related repos unavailable"

    def test_related_repos_returns_404_when_repo_missing(self, client: TestClient) -> None:
        app.dependency_overrides[_get_related_repos_use_case] = lambda: (
            MissingRelatedReposUseCase()
        )

        response = client.get(
            "/ai/related-repos",
            params={"repo_name": "missing/repo", "days": 30},
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "Repository not found"
