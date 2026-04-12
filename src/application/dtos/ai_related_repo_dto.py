"""DTOs for related repository recommendations."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from university.github.src.application.dtos.repo_metadata_dto import RepoMetadataDTO  # noqa: TC001


class RelatedRepoResultDTO(BaseModel):
    """One related repository recommendation."""

    model_config = ConfigDict(frozen=True)

    repo: RepoMetadataDTO
    similarity_score: float = Field(..., ge=0.0)
    star_count_in_window: int = Field(..., ge=0)
    shared_topics: list[str]
    why_related: list[str]


class RelatedReposResponseDTO(BaseModel):
    """Top-level response for related repository recommendations."""

    model_config = ConfigDict(frozen=True)

    source_repo: RepoMetadataDTO
    total_candidates: int = Field(..., ge=0)
    returned_results: int = Field(..., ge=0)
    results: list[RelatedRepoResultDTO]
