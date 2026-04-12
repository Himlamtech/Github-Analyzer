"""Unit tests for related repository recommendations."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest

from src.application.dtos.ai_repo_brief_dto import (
    RepoBriefActivityDTO,
    RepoBriefContextDTO,
    RepoBriefTimeseriesPointDTO,
)
from src.application.dtos.ai_search_dto import RepoSearchCandidateDTO
from src.application.dtos.repo_metadata_dto import RepoMetadataDTO
from src.application.use_cases.recommend_related_repositories import (
    RecommendRelatedRepositoriesUseCase,
)

_NOW = datetime(2026, 3, 28, 12, 0, tzinfo=UTC)


class FakeContextProvider:
    """Deterministic storage boundary for source repo context."""

    def __init__(self, context: RepoBriefContextDTO) -> None:
        self._context = context

    async def get_repo_brief_context(
        self,
        *,
        repo_name: str,
        days: int,
    ) -> RepoBriefContextDTO:
        assert repo_name == self._context.repo.repo_full_name
        assert days == self._context.window_days
        return self._context


class FakeCandidateProvider:
    """Deterministic storage boundary for recommendation candidates."""

    def __init__(self, candidates: list[RepoSearchCandidateDTO]) -> None:
        self._candidates = candidates
        self.calls: list[dict[str, object]] = []

    async def get_candidates(
        self,
        *,
        category: str | None,
        primary_language: str | None,
        min_stars: int,
        days: int,
        limit: int,
    ) -> list[RepoSearchCandidateDTO]:
        self.calls.append(
            {
                "category": category,
                "primary_language": primary_language,
                "min_stars": min_stars,
                "days": days,
                "limit": limit,
            }
        )
        return self._candidates


def _repo(
    repo_full_name: str,
    *,
    category: str,
    language: str,
    topics: list[str],
    stars: int,
    forks: int,
) -> RepoMetadataDTO:
    repo_name = repo_full_name.split("/")[-1]
    owner_login = repo_full_name.split("/")[0]
    return RepoMetadataDTO(
        repo_id=hash(repo_full_name) % 1000,
        repo_full_name=repo_full_name,
        repo_name=repo_name,
        html_url=f"https://github.com/{repo_full_name}",
        description=f"{repo_name} repository description.",
        primary_language=language,
        topics=topics,
        category=category,
        stargazers_count=stars,
        watchers_count=stars,
        forks_count=forks,
        open_issues_count=50,
        subscribers_count=300,
        owner_login=owner_login,
        owner_avatar_url="",
        license_name="MIT",
        github_created_at=_NOW - timedelta(days=500),
        github_pushed_at=_NOW - timedelta(days=2),
        rank=1,
    )


def _context() -> RepoBriefContextDTO:
    return RepoBriefContextDTO(
        repo=_repo(
            "browser-use/browser-use",
            category="Agent",
            language="Python",
            topics=["agent", "browser", "automation"],
            stars=52_000,
            forks=2_000,
        ),
        window_days=30,
        star_count_in_window=1_900,
        total_events_in_window=3_600,
        unique_actors_in_window=540,
        latest_event_at=_NOW,
        activity_breakdown=[
            RepoBriefActivityDTO(event_type="WatchEvent", event_count=1900),
        ],
        timeseries=[
            RepoBriefTimeseriesPointDTO(
                event_date=date(2026, 3, 1),
                star_count=450,
                total_events=800,
            )
        ],
    )


def _candidate(
    repo_full_name: str,
    *,
    category: str,
    language: str,
    topics: list[str],
    stars: int,
    window_stars: int,
    forks: int,
) -> RepoSearchCandidateDTO:
    repo = _repo(
        repo_full_name,
        category=category,
        language=language,
        topics=topics,
        stars=stars,
        forks=forks,
    )
    return RepoSearchCandidateDTO(
        repo=repo,
        star_count_in_window=window_stars,
        search_document=" ".join(
            [
                repo.repo_full_name,
                repo.primary_language,
                repo.category,
                " ".join(repo.topics),
                repo.description,
            ]
        ),
    )


class TestRecommendRelatedRepositoriesUseCase:
    async def test_execute_returns_ranked_related_repositories(self) -> None:
        context = _context()
        candidate_provider = FakeCandidateProvider(
            [
                _candidate(
                    "browserbase/stagehand",
                    category="Agent",
                    language="Python",
                    topics=["agent", "browser", "automation"],
                    stars=26_000,
                    window_stars=1_100,
                    forks=1_200,
                ),
                _candidate(
                    "langchain-ai/langchain",
                    category="Agent",
                    language="Python",
                    topics=["agent", "llm", "framework"],
                    stars=104_000,
                    window_stars=800,
                    forks=12_000,
                ),
                _candidate(
                    "tensorflow/tensorflow",
                    category="Other",
                    language="C++",
                    topics=["ml", "framework"],
                    stars=190_000,
                    window_stars=50,
                    forks=74_000,
                ),
            ]
        )
        use_case = RecommendRelatedRepositoriesUseCase(
            FakeContextProvider(context),
            candidate_provider,
            candidate_limit=10,
        )

        result = await use_case.execute(
            repo_name="browser-use/browser-use",
            days=30,
            limit=5,
        )

        assert result.source_repo.repo_full_name == "browser-use/browser-use"
        assert result.results[0].repo.repo_full_name == "browserbase/stagehand"
        assert result.results[0].shared_topics == ["agent", "automation", "browser"]
        assert all(
            candidate.repo.repo_full_name != "tensorflow/tensorflow"
            for candidate in result.results
        )
        assert candidate_provider.calls == [
            {
                "category": "Agent",
                "primary_language": None,
                "min_stars": 2600,
                "days": 30,
                "limit": 25,
            }
        ]

    async def test_execute_excludes_source_repo_and_respects_limit(self) -> None:
        context = _context()
        candidates = [
            _candidate(
                "browser-use/browser-use",
                category="Agent",
                language="Python",
                topics=["agent", "browser", "automation"],
                stars=52_000,
                window_stars=1_900,
                forks=2_000,
            ),
            _candidate(
                "browserbase/stagehand",
                category="Agent",
                language="Python",
                topics=["agent", "browser", "automation"],
                stars=26_000,
                window_stars=1_100,
                forks=1_200,
            ),
            _candidate(
                "langchain-ai/langchain",
                category="Agent",
                language="Python",
                topics=["agent", "llm", "framework"],
                stars=104_000,
                window_stars=800,
                forks=12_000,
            ),
            _candidate(
                "tensorflow/tensorflow",
                category="Other",
                language="C++",
                topics=["ml", "framework"],
                stars=190_000,
                window_stars=50,
                forks=74_000,
            ),
        ]
        candidate_provider = FakeCandidateProvider(candidates)
        use_case = RecommendRelatedRepositoriesUseCase(
            FakeContextProvider(context),
            candidate_provider,
            candidate_limit=10,
        )

        result = await use_case.execute(
            repo_name="browser-use/browser-use",
            days=30,
            limit=1,
        )

        assert result.returned_results == 1
        assert result.results[0].repo.repo_full_name == "browserbase/stagehand"
        assert all(
            candidate.repo.repo_full_name != "browser-use/browser-use"
            for candidate in result.results
        )
        assert all(
            candidate.repo.repo_full_name != "tensorflow/tensorflow"
            for candidate in result.results
        )
        assert candidate_provider.calls[0]["limit"] == 10

    @pytest.mark.parametrize(
        ("stars", "expected"),
        [
            (600, 1000),
            (52_000, 2600),
            (400_000, 10_000),
        ],
    )
    async def test_execute_uses_bounded_minimum_star_threshold(
        self,
        stars: int,
        expected: int,
    ) -> None:
        context = _context().model_copy(
            update={
                "repo": _context().repo.model_copy(
                    update={"stargazers_count": stars},
                )
            }
        )
        candidate_provider = FakeCandidateProvider(
            [
                _candidate(
                    "browserbase/stagehand",
                    category="Agent",
                    language="Python",
                    topics=["agent", "browser", "automation"],
                    stars=26_000,
                    window_stars=1_100,
                    forks=1_200,
                )
            ]
        )
        use_case = RecommendRelatedRepositoriesUseCase(
            FakeContextProvider(context),
            candidate_provider,
            candidate_limit=8,
        )

        await use_case.execute(
            repo_name="browser-use/browser-use",
            days=30,
            limit=3,
        )

        assert candidate_provider.calls[0]["min_stars"] == expected
