"""DTOs for grounded AI market brief responses."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from university.github.src.application.dtos.repo_metadata_dto import RepoMetadataDTO  # noqa: TC001


class MarketBreakoutRepoDTO(BaseModel):
    """One breakout repository highlighted in the market brief."""

    model_config = ConfigDict(frozen=True)

    repo: RepoMetadataDTO
    star_count_in_window: int = Field(..., ge=0)
    total_events_in_window: int = Field(..., ge=0)
    unique_actors_in_window: int = Field(..., ge=0)
    momentum_score: float = Field(..., ge=0.0)


class MarketCategoryMoverDTO(BaseModel):
    """Momentum snapshot for one repository category."""

    model_config = ConfigDict(frozen=True)

    category: str
    active_repo_count: int = Field(..., ge=0)
    total_stars_in_window: int = Field(..., ge=0)
    total_events_in_window: int = Field(..., ge=0)
    leader_repo_name: str
    leader_stars_in_window: int = Field(..., ge=0)
    share_of_window_stars: float = Field(..., ge=0.0)


class MarketTopicShiftDTO(BaseModel):
    """Topic-level shift signal within the selected time window."""

    model_config = ConfigDict(frozen=True)

    topic: str
    repo_count: int = Field(..., ge=0)
    star_count_in_window: int = Field(..., ge=0)


class MarketBriefContextDTO(BaseModel):
    """Storage-backed context used to generate the market brief."""

    model_config = ConfigDict(frozen=True)

    window_days: int = Field(..., ge=1, le=365)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))
    breakout_repos: list[MarketBreakoutRepoDTO]
    category_movers: list[MarketCategoryMoverDTO]
    topic_shifts: list[MarketTopicShiftDTO]


class MarketBriefResponseDTO(BaseModel):
    """Final AI market brief returned to the frontend."""

    model_config = ConfigDict(frozen=True)

    window_days: int = Field(..., ge=1, le=365)
    generated_at: datetime
    retrieval_mode: Literal["template", "model"]
    headline: str
    summary: str
    key_takeaways: list[str]
    watchouts: list[str]
    breakout_repos: list[MarketBreakoutRepoDTO]
    category_movers: list[MarketCategoryMoverDTO]
    topic_shifts: list[MarketTopicShiftDTO]
