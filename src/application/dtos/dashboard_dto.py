"""DTOs for dashboard query responses."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from src.application.dtos.repo_metadata_dto import RepoMetadataDTO  # noqa: TC001


class TopRepoResponseDTO(BaseModel):
    """One repository ranked in the top repositories leaderboard."""

    model_config = ConfigDict(frozen=True)

    repo: RepoMetadataDTO
    star_count_in_window: int = Field(..., ge=0)
    star_delta: int = 0


class TrendingRepoResponseDTO(BaseModel):
    """One repository ranked in the current momentum leaderboard."""

    model_config = ConfigDict(frozen=True)

    repo: RepoMetadataDTO
    star_count_in_window: int = Field(..., ge=0)
    growth_rank: int = Field(..., ge=1)


class TopicBreakdownDTO(BaseModel):
    """Topic-level star activity breakdown."""

    model_config = ConfigDict(frozen=True)

    topic: str
    star_count: int = Field(..., ge=0)
    repo_count: int = Field(..., ge=0)


class LanguageBreakdownDTO(BaseModel):
    """Language-level star activity breakdown."""

    model_config = ConfigDict(frozen=True)

    language: str
    star_count: int = Field(..., ge=0)
    repo_count: int = Field(..., ge=0)


class TimeseriesPointDTO(BaseModel):
    """Daily repository activity point."""

    model_config = ConfigDict(frozen=True)

    event_date: date
    star_count: int = Field(..., ge=0)
    total_events: int = Field(..., ge=0)


class CategorySummaryDTO(BaseModel):
    """Category leaderboard row."""

    model_config = ConfigDict(frozen=True)

    category: str
    repo_count: int = Field(..., ge=0)
    total_stars: int = Field(..., ge=0)
    top_repo_name: str = ""
    top_repo_stars: int = Field(..., ge=0)
    weekly_star_delta: int = 0


class ShockMoverDTO(BaseModel):
    """Repository movement snapshot for the current vs prior window."""

    model_config = ConfigDict(frozen=True)

    repo: RepoMetadataDTO
    star_count_in_window: int = Field(..., ge=0)
    previous_star_count_in_window: int = Field(..., ge=0)
    unique_actors_in_window: int = Field(..., ge=0)
    weekly_percent_gain: float
    window_over_window_ratio: float
    rank: int = Field(..., ge=1)


class ShockMoversResponseDTO(BaseModel):
    """Grouped market movers for the current window."""

    model_config = ConfigDict(frozen=True)

    window_days: int = Field(..., ge=1)
    absolute_movers: list[ShockMoverDTO]
    percentage_movers: list[ShockMoverDTO]


class TopicRotationDTO(BaseModel):
    """Topic momentum vs the previous window."""

    model_config = ConfigDict(frozen=True)

    topic: str
    current_star_count: int = Field(..., ge=0)
    previous_star_count: int = Field(..., ge=0)
    star_delta: int
    repo_count: int = Field(..., ge=0)
    rank: int = Field(..., ge=1)
