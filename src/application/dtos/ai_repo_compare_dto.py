"""DTOs for grounded repository comparison responses."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from university.github.src.application.dtos.repo_metadata_dto import RepoMetadataDTO  # noqa: TC001


class RepoCompareMetricDTO(BaseModel):
    """One compared metric across two repositories."""

    model_config = ConfigDict(frozen=True)

    key: str
    label: str
    base_value: int = Field(..., ge=0)
    compare_value: int = Field(..., ge=0)
    winner: Literal["base", "compare", "tie"]


class RepoCompareResponseDTO(BaseModel):
    """Final AI response comparing two repositories."""

    model_config = ConfigDict(frozen=True)

    base_repo: RepoMetadataDTO
    compare_repo: RepoMetadataDTO
    window_days: int = Field(..., ge=1)
    retrieval_mode: Literal["template", "model"]
    overall_winner: Literal["base", "compare", "tie"]
    headline: str
    summary: str
    key_differences: list[str]
    when_to_choose_base: list[str]
    when_to_choose_compare: list[str]
    metric_snapshot: list[RepoCompareMetricDTO]
