"""Unit tests for the AI repository search use case."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from src.application.dtos.ai_search_dto import RepoSearchCandidateDTO
from src.application.dtos.repo_metadata_dto import RepoMetadataDTO
from src.application.use_cases.search_repositories import SearchRepositoriesUseCase
from src.domain.exceptions import EmbeddingServiceError, ValidationError

_NOW = datetime(2026, 3, 28, 12, 0, tzinfo=UTC)


class FakeCandidateProvider:
    """Deterministic storage boundary for search candidates."""

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


class FakeEmbeddingService:
    """Embedding boundary returning precomputed vectors."""

    def __init__(self, vectors: list[list[float]]) -> None:
        self._vectors = vectors

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        assert len(texts) == len(self._vectors)
        return self._vectors


class FailingEmbeddingService:
    """Embedding boundary that simulates an unavailable semantic backend."""

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        raise EmbeddingServiceError("ollama offline")


def _candidate(
    *,
    repo_id: int,
    full_name: str,
    description: str,
    category: str,
    language: str,
    topics: list[str],
    stars: int,
    star_count_in_window: int,
) -> RepoSearchCandidateDTO:
    repo_name = full_name.split("/")[-1]
    owner_login = full_name.split("/")[0]
    repo = RepoMetadataDTO(
        repo_id=repo_id,
        repo_full_name=full_name,
        repo_name=repo_name,
        html_url=f"https://github.com/{full_name}",
        description=description,
        primary_language=language,
        topics=topics,
        category=category,
        stargazers_count=stars,
        watchers_count=stars,
        forks_count=stars // 10,
        open_issues_count=12,
        subscribers_count=100,
        owner_login=owner_login,
        owner_avatar_url="",
        license_name="MIT",
        github_created_at=_NOW,
        github_pushed_at=_NOW,
        rank=repo_id,
    )
    return RepoSearchCandidateDTO(
        repo=repo,
        star_count_in_window=star_count_in_window,
        search_document=" ".join(
            [full_name, repo_name, owner_login, language, category, " ".join(topics), description]
        ),
    )


class TestSearchRepositoriesUseCase:
    async def test_execute_returns_explainable_lexical_results(self) -> None:
        provider = FakeCandidateProvider(
            [
                _candidate(
                    repo_id=1,
                    full_name="browser-use/browser-use",
                    description="Browser automation agent for web workflows in Python.",
                    category="Agent",
                    language="Python",
                    topics=["agent", "browser", "automation"],
                    stars=52_000,
                    star_count_in_window=1_900,
                ),
                _candidate(
                    repo_id=2,
                    full_name="huggingface/transformers",
                    description="Transformers library for PyTorch, TensorFlow, and JAX.",
                    category="LLM",
                    language="Python",
                    topics=["llm", "transformer", "nlp"],
                    stars=145_000,
                    star_count_in_window=850,
                ),
            ]
        )
        use_case = SearchRepositoriesUseCase(
            provider,
            embedding_service=None,
            semantic_enabled=False,
            candidate_limit=10,
        )

        result = await use_case.execute(
            query="browser automation agents python",
            category="Agent",
            primary_language="Python",
            min_stars=10_000,
            days=30,
            limit=5,
        )

        assert result.retrieval_mode == "lexical"
        assert result.results[0].repo.repo_full_name == "browser-use/browser-use"
        assert "browser" in result.results[0].matched_terms
        assert any("Topic overlap" in reason for reason in result.results[0].why_matched)
        assert provider.calls[0]["category"] == "Agent"
        assert provider.calls[0]["primary_language"] == "Python"

    async def test_execute_uses_semantic_rerank_when_embeddings_available(self) -> None:
        provider = FakeCandidateProvider(
            [
                _candidate(
                    repo_id=1,
                    full_name="langchain-ai/langchain",
                    description="Framework for LLM apps and agent orchestration.",
                    category="Agent",
                    language="Python",
                    topics=["agent", "rag"],
                    stars=104_000,
                    star_count_in_window=600,
                ),
                _candidate(
                    repo_id=2,
                    full_name="browser-use/browser-use",
                    description="Browser automation agent for web navigation workflows.",
                    category="Agent",
                    language="Python",
                    topics=["browser", "web", "automation"],
                    stars=52_000,
                    star_count_in_window=1_900,
                ),
            ]
        )
        embedding_service = FakeEmbeddingService(
            [
                [1.0, 0.0],
                [0.2, 0.98],
                [0.98, 0.2],
            ]
        )
        use_case = SearchRepositoriesUseCase(
            provider,
            embedding_service=embedding_service,
            semantic_enabled=True,
            candidate_limit=10,
        )

        result = await use_case.execute(
            query="tools for web agent navigation",
            category=None,
            primary_language=None,
            min_stars=10_000,
            days=30,
            limit=5,
        )

        assert result.retrieval_mode == "hybrid"
        assert result.results[0].repo.repo_full_name == "browser-use/browser-use"
        assert result.results[0].semantic_score is not None

    async def test_execute_falls_back_to_lexical_when_embeddings_fail(self) -> None:
        provider = FakeCandidateProvider(
            [
                _candidate(
                    repo_id=1,
                    full_name="crewAIInc/crewAI",
                    description="Agent orchestration framework for collaborative AI teams.",
                    category="Agent",
                    language="Python",
                    topics=["agent", "automation"],
                    stars=35_000,
                    star_count_in_window=700,
                )
            ]
        )
        use_case = SearchRepositoriesUseCase(
            provider,
            embedding_service=FailingEmbeddingService(),
            semantic_enabled=True,
            candidate_limit=10,
        )

        result = await use_case.execute(
            query="agent orchestration teams",
            category=None,
            primary_language=None,
            min_stars=10_000,
            days=30,
            limit=5,
        )

        assert result.retrieval_mode == "lexical"
        assert result.results[0].repo.repo_full_name == "crewAIInc/crewAI"
        assert result.results[0].semantic_score is None

    async def test_execute_blank_query_raises_validation_error(self) -> None:
        provider = FakeCandidateProvider([])
        use_case = SearchRepositoriesUseCase(
            provider,
            embedding_service=None,
            semantic_enabled=False,
            candidate_limit=10,
        )

        with pytest.raises(ValidationError, match="at least 2"):
            await use_case.execute(
                query=" ",
                category=None,
                primary_language=None,
                min_stars=10_000,
                days=30,
                limit=5,
            )
