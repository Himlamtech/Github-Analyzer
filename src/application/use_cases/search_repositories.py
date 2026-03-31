"""Use case for explainable AI repository discovery search."""

from __future__ import annotations

from dataclasses import dataclass
import math
import re
from typing import TYPE_CHECKING, Protocol

import structlog

from src.application.dtos.ai_search_dto import (
    RepoSearchCandidateDTO,
    RepoSearchFiltersDTO,
    RepoSearchResponseDTO,
    RepoSearchResultDTO,
)
from src.domain.exceptions import EmbeddingServiceError, ValidationError

logger = structlog.get_logger(__name__)

_TOKEN_PATTERN = re.compile(r"[a-z0-9][a-z0-9+.#/-]*")

if TYPE_CHECKING:
    from collections.abc import Sequence


class RepoSearchCandidateProviderProtocol(Protocol):
    """Storage-backed provider for search candidates."""

    async def get_candidates(
        self,
        *,
        category: str | None,
        primary_language: str | None,
        min_stars: int,
        days: int,
        limit: int,
    ) -> list[RepoSearchCandidateDTO]: ...


class EmbeddingServiceProtocol(Protocol):
    """Semantic embedding service used for reranking."""

    async def embed_texts(self, texts: Sequence[str]) -> list[list[float]]: ...


@dataclass(frozen=True)
class _LexicalBreakdown:
    score: float
    matched_terms: list[str]
    why_matched: list[str]


class SearchRepositoriesUseCase:
    """Search repositories with lexical ranking and optional semantic reranking."""

    def __init__(
        self,
        candidate_provider: RepoSearchCandidateProviderProtocol,
        *,
        embedding_service: EmbeddingServiceProtocol | None = None,
        semantic_enabled: bool = True,
        candidate_limit: int = 40,
    ) -> None:
        self._candidate_provider = candidate_provider
        self._embedding_service = embedding_service
        self._semantic_enabled = semantic_enabled
        self._candidate_limit = candidate_limit

    async def execute(
        self,
        *,
        query: str,
        category: str | None,
        primary_language: str | None,
        min_stars: int,
        days: int,
        limit: int,
    ) -> RepoSearchResponseDTO:
        """Return the top explainable repository matches for a user query."""
        normalized_query = _normalize_query(query)
        if len(normalized_query) < 2:
            raise ValidationError("Search query must contain at least 2 non-space characters.")

        filters = RepoSearchFiltersDTO(
            category=_clean_optional_text(category),
            primary_language=_clean_optional_text(primary_language),
            min_stars=min_stars,
            days=days,
        )
        candidates = await self._candidate_provider.get_candidates(
            category=filters.category,
            primary_language=filters.primary_language,
            min_stars=filters.min_stars,
            days=filters.days,
            limit=max(limit * 4, self._candidate_limit),
        )
        if not candidates:
            return RepoSearchResponseDTO(
                query=query,
                normalized_query=normalized_query,
                retrieval_mode="lexical",
                total_candidates=0,
                returned_results=0,
                filters=filters,
                results=[],
            )

        query_terms = _tokenize(normalized_query)
        semantic_scores = await self._embed_candidates(normalized_query, candidates)
        retrieval_mode = "hybrid" if semantic_scores is not None else "lexical"
        results = self._build_results(
            candidates=candidates,
            query=normalized_query,
            query_terms=query_terms,
            semantic_scores=semantic_scores,
            days=filters.days,
            limit=limit,
        )
        return RepoSearchResponseDTO(
            query=query,
            normalized_query=normalized_query,
            retrieval_mode=retrieval_mode,
            total_candidates=len(candidates),
            returned_results=len(results),
            filters=filters,
            results=results,
        )

    async def _embed_candidates(
        self,
        query: str,
        candidates: list[RepoSearchCandidateDTO],
    ) -> dict[str, float] | None:
        if not self._semantic_enabled or self._embedding_service is None:
            return None

        texts = [query, *[candidate.search_document for candidate in candidates]]
        try:
            vectors = await self._embedding_service.embed_texts(texts)
        except EmbeddingServiceError as exc:
            logger.warning("ai_search.semantic_unavailable", error=str(exc))
            return None

        if len(vectors) != len(texts):
            logger.warning(
                "ai_search.semantic_vector_mismatch",
                expected=len(texts),
                received=len(vectors),
            )
            return None

        query_vector = vectors[0]
        semantic_scores: dict[str, float] = {}
        for candidate, vector in zip(candidates, vectors[1:], strict=True):
            semantic_scores[candidate.repo.repo_full_name] = round(
                _normalize_cosine_score(_cosine_similarity(query_vector, vector)),
                4,
            )
        return semantic_scores

    def _build_results(
        self,
        *,
        candidates: list[RepoSearchCandidateDTO],
        query: str,
        query_terms: list[str],
        semantic_scores: dict[str, float] | None,
        days: int,
        limit: int,
    ) -> list[RepoSearchResultDTO]:
        scored_results: list[RepoSearchResultDTO] = []
        for candidate in candidates:
            lexical = _score_lexically(candidate, query, query_terms)
            popularity = _popularity_score(candidate)
            semantic_score = None
            if semantic_scores is not None:
                semantic_score = semantic_scores.get(candidate.repo.repo_full_name)
            if not _should_include_candidate(lexical.score, semantic_score):
                continue

            reasons = _enrich_reasons(
                lexical.why_matched,
                semantic_score,
                candidate.star_count_in_window,
                days,
                candidate.repo.stargazers_count,
            )
            scored_results.append(
                RepoSearchResultDTO(
                    repo=candidate.repo,
                    star_count_in_window=candidate.star_count_in_window,
                    score=_overall_score(lexical.score, popularity, semantic_score),
                    lexical_score=lexical.score,
                    semantic_score=semantic_score,
                    popularity_score=popularity,
                    matched_terms=lexical.matched_terms,
                    why_matched=reasons,
                )
            )

        scored_results.sort(
            key=lambda result: (
                result.score,
                result.lexical_score,
                result.semantic_score or 0.0,
                result.star_count_in_window,
                result.repo.stargazers_count,
            ),
            reverse=True,
        )
        return scored_results[:limit]


def _normalize_query(query: str) -> str:
    return " ".join(query.strip().lower().split())


def _clean_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _tokenize(text: str) -> list[str]:
    unique_terms = dict.fromkeys(_TOKEN_PATTERN.findall(text.lower()))
    return list(unique_terms)


def _score_lexically(
    candidate: RepoSearchCandidateDTO,
    query: str,
    query_terms: list[str],
) -> _LexicalBreakdown:
    repo = candidate.repo
    repo_full_name = repo.repo_full_name.lower()
    repo_name = repo.repo_name.lower()
    owner_login = repo.owner_login.lower()
    description = repo.description.lower()
    primary_language = repo.primary_language.lower()
    category = repo.category.lower()
    topics = [topic.lower() for topic in repo.topics]

    raw_score = 0.0
    matched_terms: set[str] = set()
    name_hits: set[str] = set()
    topic_hits: set[str] = set()
    description_hits: set[str] = set()
    language_hits: set[str] = set()
    category_hits: set[str] = set()

    if query in repo_full_name:
        raw_score += 4.0
    if query in description:
        raw_score += 2.5

    for term in query_terms:
        if term in repo_full_name or term in repo_name or term in owner_login:
            raw_score += 3.0
            name_hits.add(term)
            matched_terms.add(term)
            continue
        if any(term in topic for topic in topics):
            raw_score += 2.5
            topic_hits.add(term)
            matched_terms.add(term)
            continue
        if primary_language and term in primary_language:
            raw_score += 2.25
            language_hits.add(term)
            matched_terms.add(term)
            continue
        if category and term in category:
            raw_score += 2.25
            category_hits.add(term)
            matched_terms.add(term)
            continue
        if term in description:
            raw_score += 1.5
            description_hits.add(term)
            matched_terms.add(term)

    if query_terms and all(term in candidate.search_document.lower() for term in query_terms):
        raw_score += min(3.0, len(query_terms) * 0.75)

    reasons: list[str] = []
    if name_hits:
        reasons.append(f"Repo identity matches: {', '.join(sorted(name_hits))}.")
    if topic_hits:
        reasons.append(f"Topic overlap: {', '.join(sorted(topic_hits))}.")
    if language_hits:
        reasons.append(f"Language signal: {repo.primary_language}.")
    if category_hits:
        reasons.append(f"Category signal: {repo.category}.")
    if description_hits:
        reasons.append(f"Description mentions: {', '.join(sorted(description_hits))}.")
    if not reasons and query in candidate.search_document.lower():
        reasons.append("Query phrase appears in repository metadata.")

    max_score = 4.0 + max(1, len(query_terms)) * 3.0 + 3.0
    lexical_score = round(min(raw_score / max_score, 1.0), 4)
    return _LexicalBreakdown(
        score=lexical_score,
        matched_terms=sorted(matched_terms),
        why_matched=reasons,
    )


def _popularity_score(candidate: RepoSearchCandidateDTO) -> float:
    stars_component = min(math.log1p(candidate.repo.stargazers_count) / 12.0, 1.0)
    momentum_component = min(math.log1p(candidate.star_count_in_window) / 8.0, 1.0)
    return round((stars_component * 0.6) + (momentum_component * 0.4), 4)


def _overall_score(
    lexical_score: float,
    popularity_score: float,
    semantic_score: float | None,
) -> float:
    if semantic_score is None:
        return round((lexical_score * 0.75) + (popularity_score * 0.25), 4)
    return round(
        (lexical_score * 0.4) + (semantic_score * 0.45) + (popularity_score * 0.15),
        4,
    )


def _should_include_candidate(
    lexical_score: float,
    semantic_score: float | None,
) -> bool:
    if semantic_score is None:
        return lexical_score > 0.0
    return lexical_score > 0.0 or semantic_score >= 0.58


def _enrich_reasons(
    reasons: list[str],
    semantic_score: float | None,
    star_count_in_window: int,
    days: int,
    stargazers_count: int,
) -> list[str]:
    enriched = list(reasons)
    if semantic_score is not None and semantic_score >= 0.68:
        enriched.append("Semantic reranker found a strong conceptual match.")
    if star_count_in_window > 0:
        enriched.append(f"Recent momentum: +{star_count_in_window:,} stars in {days}d.")
    elif stargazers_count >= 20_000:
        enriched.append(f"Established project with {stargazers_count:,} total stars.")
    return enriched[:4]


def _cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right) or not left:
        return 0.0
    numerator = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return numerator / (left_norm * right_norm)


def _normalize_cosine_score(score: float) -> float:
    return max(0.0, min((score + 1.0) / 2.0, 1.0))
