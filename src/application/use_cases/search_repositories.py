"""Use case for explainable AI repository discovery search."""

from __future__ import annotations

from dataclasses import dataclass
import math
import re
from typing import Protocol

import structlog

from src.application.dtos.ai_search_dto import (
    RepoSearchCandidateDTO,
    RepoSearchFiltersDTO,
    RepoSearchResponseDTO,
    RepoSearchResultDTO,
)
from src.domain.exceptions import ValidationError

logger = structlog.get_logger(__name__)

_TOKEN_PATTERN = re.compile(r"[a-z0-9][a-z0-9+.#/-]*")


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


@dataclass(frozen=True)
class _LexicalBreakdown:
    score: float
    matched_terms: list[str]
    why_matched: list[str]


class SearchRepositoriesUseCase:
    """Search repositories with lexical ranking."""

    def __init__(
        self,
        candidate_provider: RepoSearchCandidateProviderProtocol,
        *,
        candidate_limit: int = 40,
    ) -> None:
        self._candidate_provider = candidate_provider
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
        results = self._build_results(
            candidates=candidates,
            query=normalized_query,
            query_terms=query_terms,
            days=filters.days,
            limit=limit,
        )
        return RepoSearchResponseDTO(
            query=query,
            normalized_query=normalized_query,
            retrieval_mode="lexical",
            total_candidates=len(candidates),
            returned_results=len(results),
            filters=filters,
            results=results,
        )

    def _build_results(
        self,
        *,
        candidates: list[RepoSearchCandidateDTO],
        query: str,
        query_terms: list[str],
        days: int,
        limit: int,
    ) -> list[RepoSearchResultDTO]:
        scored_results: list[RepoSearchResultDTO] = []
        for candidate in candidates:
            lexical = _score_lexically(candidate, query, query_terms)
            popularity = _popularity_score(candidate)
            if lexical.score <= 0.0:
                continue

            reasons = _enrich_reasons(
                lexical.why_matched,
                candidate.star_count_in_window,
                days,
                candidate.repo.stargazers_count,
            )
            scored_results.append(
                RepoSearchResultDTO(
                    repo=candidate.repo,
                    star_count_in_window=candidate.star_count_in_window,
                    score=_overall_score(lexical.score, popularity),
                    lexical_score=lexical.score,
                    popularity_score=popularity,
                    matched_terms=lexical.matched_terms,
                    why_matched=reasons,
                )
            )

        scored_results.sort(
            key=lambda result: (
                result.score,
                result.lexical_score,
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
) -> float:
    return round((lexical_score * 0.75) + (popularity_score * 0.25), 4)


def _enrich_reasons(
    reasons: list[str],
    star_count_in_window: int,
    days: int,
    stargazers_count: int,
) -> list[str]:
    enriched = list(reasons)
    if star_count_in_window > 0:
        enriched.append(f"Recent momentum: +{star_count_in_window:,} stars in {days}d.")
    elif stargazers_count >= 20_000:
        enriched.append(f"Established project with {stargazers_count:,} total stars.")
    return enriched[:4]
