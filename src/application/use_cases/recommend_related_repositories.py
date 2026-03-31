"""Use case for recommending related repositories."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from src.application.dtos.ai_related_repo_dto import (
    RelatedRepoResultDTO,
    RelatedReposResponseDTO,
)

if TYPE_CHECKING:
    from src.application.dtos.ai_repo_brief_dto import RepoBriefContextDTO
    from src.application.dtos.ai_search_dto import RepoSearchCandidateDTO


class RepoInsightContextProviderProtocol(Protocol):
    """Storage-backed provider for repository insight context."""

    async def get_repo_brief_context(
        self,
        *,
        repo_name: str,
        days: int,
    ) -> RepoBriefContextDTO: ...


class RepoSearchCandidateProviderProtocol(Protocol):
    """Storage-backed provider for recommendation candidates."""

    async def get_candidates(
        self,
        *,
        category: str | None,
        primary_language: str | None,
        min_stars: int,
        days: int,
        limit: int,
    ) -> list[RepoSearchCandidateDTO]: ...


class RecommendRelatedRepositoriesUseCase:
    """Recommend repositories adjacent to a selected repository."""

    def __init__(
        self,
        context_provider: RepoInsightContextProviderProtocol,
        candidate_provider: RepoSearchCandidateProviderProtocol,
        *,
        candidate_limit: int = 40,
    ) -> None:
        self._context_provider = context_provider
        self._candidate_provider = candidate_provider
        self._candidate_limit = candidate_limit

    async def execute(
        self,
        *,
        repo_name: str,
        days: int,
        limit: int,
    ) -> RelatedReposResponseDTO:
        """Return repositories related to the provided source repository."""
        source_context = await self._context_provider.get_repo_brief_context(
            repo_name=repo_name,
            days=days,
        )
        min_stars = _related_repo_min_stars(source_context.repo.stargazers_count)
        candidates = await self._candidate_provider.get_candidates(
            category=source_context.repo.category or None,
            primary_language=None,
            min_stars=min_stars,
            days=days,
            limit=max(limit * 5, self._candidate_limit),
        )
        results = _rank_candidates(source_context, candidates, limit)
        return RelatedReposResponseDTO(
            source_repo=source_context.repo,
            total_candidates=len(candidates),
            returned_results=len(results),
            results=results,
        )


def _related_repo_min_stars(stars: int) -> int:
    """Keep the candidate pool large enough without drifting into tiny repos."""
    return max(min(stars // 20, 10_000), 1_000)


def _rank_candidates(
    source_context: RepoBriefContextDTO,
    candidates: list[RepoSearchCandidateDTO],
    limit: int,
) -> list[RelatedRepoResultDTO]:
    source_topics = {topic.lower() for topic in source_context.repo.topics}
    results: list[RelatedRepoResultDTO] = []
    for candidate in candidates:
        if candidate.repo.repo_full_name == source_context.repo.repo_full_name:
            continue
        shared_topics = sorted(
            source_topics.intersection({topic.lower() for topic in candidate.repo.topics})
        )
        similarity_score = _similarity_score(source_context, candidate, shared_topics)
        if similarity_score < 0.25:
            continue
        results.append(
            RelatedRepoResultDTO(
                repo=candidate.repo,
                similarity_score=similarity_score,
                star_count_in_window=candidate.star_count_in_window,
                shared_topics=shared_topics,
                why_related=_why_related(source_context, candidate, shared_topics),
            )
        )

    results.sort(
        key=lambda item: (
            item.similarity_score,
            item.star_count_in_window,
            item.repo.stargazers_count,
        ),
        reverse=True,
    )
    return results[:limit]


def _similarity_score(
    source_context: RepoBriefContextDTO,
    candidate: RepoSearchCandidateDTO,
    shared_topics: list[str],
) -> float:
    source_topics = {topic.lower() for topic in source_context.repo.topics}
    topic_score = len(shared_topics) / max(len(source_topics), 1) if source_topics else 0.0
    category_score = 1.0 if candidate.repo.category == source_context.repo.category else 0.0
    language_score = (
        1.0
        if candidate.repo.primary_language
        and candidate.repo.primary_language == source_context.repo.primary_language
        else 0.0
    )
    scale_score = _ratio_score(
        source_context.repo.stargazers_count,
        candidate.repo.stargazers_count,
    )
    momentum_score = _ratio_score(
        max(source_context.star_count_in_window, 1),
        max(candidate.star_count_in_window, 1),
    )
    description_score = _description_overlap_score(
        source_context.repo.description,
        candidate.repo.description,
    )
    return round(
        (topic_score * 0.4)
        + (category_score * 0.2)
        + (language_score * 0.1)
        + (scale_score * 0.15)
        + (momentum_score * 0.1)
        + (description_score * 0.05),
        4,
    )


def _ratio_score(left: int, right: int) -> float:
    larger = max(left, right, 1)
    smaller = min(left, right)
    return round(smaller / larger, 4)


def _description_overlap_score(left: str, right: str) -> float:
    left_terms = {term for term in left.lower().split() if len(term) >= 4}
    right_terms = {term for term in right.lower().split() if len(term) >= 4}
    if not left_terms or not right_terms:
        return 0.0
    overlap = len(left_terms.intersection(right_terms))
    union = len(left_terms.union(right_terms))
    return round(overlap / union, 4) if union else 0.0


def _why_related(
    source_context: RepoBriefContextDTO,
    candidate: RepoSearchCandidateDTO,
    shared_topics: list[str],
) -> list[str]:
    reasons: list[str] = []
    if shared_topics:
        reasons.append(f"Shared topics: {', '.join(shared_topics[:3])}.")
    if candidate.repo.category == source_context.repo.category:
        reasons.append(f"Same category: {candidate.repo.category}.")
    if (
        candidate.repo.primary_language
        and candidate.repo.primary_language == source_context.repo.primary_language
    ):
        reasons.append(f"Same language stack: {candidate.repo.primary_language}.")
    if (
        _ratio_score(
            source_context.repo.stargazers_count,
            candidate.repo.stargazers_count,
        )
        >= 0.5
    ):
        reasons.append("Comparable ecosystem scale by GitHub stars.")
    if (
        _ratio_score(
            max(source_context.star_count_in_window, 1),
            max(candidate.star_count_in_window, 1),
        )
        >= 0.5
    ):
        reasons.append("Recent momentum sits in a similar range.")
    return reasons[:4]
