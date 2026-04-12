"""DTOs for explainable AI repository search responses."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from university.github.src.application.dtos.repo_metadata_dto import RepoMetadataDTO  # noqa: TC001


class RepoSearchFiltersDTO(BaseModel):
    """Normalized filters applied to an AI search request."""

    model_config = ConfigDict(frozen=True)

    category: str | None = None
    primary_language: str | None = None
    min_stars: int = Field(..., ge=0)
    days: int = Field(..., ge=1, le=365)


class RepoSearchCandidateDTO(BaseModel):
    """Candidate repository fetched from storage before reranking."""

    model_config = ConfigDict(frozen=True)

    repo: RepoMetadataDTO
    star_count_in_window: int = Field(..., ge=0)
    search_document: str = Field(default="", description="Dense text used for search scoring.")


class RepoSearchResultDTO(BaseModel):
    """Explainable AI search result for one repository."""

    model_config = ConfigDict(frozen=True)

    repo: RepoMetadataDTO
    star_count_in_window: int = Field(..., ge=0)
    score: float = Field(..., ge=0.0)
    lexical_score: float = Field(..., ge=0.0)
    semantic_score: float | None = Field(default=None, ge=0.0)
    popularity_score: float = Field(..., ge=0.0)
    matched_terms: list[str]
    why_matched: list[str]


class RepoSearchResponseDTO(BaseModel):
    """Top-level response for ``GET /ai/search``."""

    model_config = ConfigDict(frozen=True)

    query: str
    normalized_query: str
    retrieval_mode: Literal["lexical", "hybrid"]
    total_candidates: int = Field(..., ge=0)
    returned_results: int = Field(..., ge=0)
    filters: RepoSearchFiltersDTO
    results: list[RepoSearchResultDTO]
