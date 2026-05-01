"""DTOs for repo metadata and all dashboard API response shapes.

All models use ``ConfigDict(frozen=True)`` matching the existing DTO convention.
These are the wire formats returned by the dashboard API endpoints.
"""

from __future__ import annotations

from datetime import date, datetime  # noqa: TC003

from pydantic import BaseModel, ConfigDict, Field


class RepoMetadataDTO(BaseModel):
    """Full repo metadata snapshot returned by dashboard endpoints.

    Maps 1-to-1 to the ``repo_metadata`` ClickHouse table.
    """

    model_config = ConfigDict(frozen=True)

    repo_id: int
    repo_full_name: str
    repo_name: str
    html_url: str
    description: str
    primary_language: str
    topics: list[str]
    category: str
    stargazers_count: int
    watchers_count: int
    forks_count: int
    open_issues_count: int
    subscribers_count: int
    owner_login: str
    owner_avatar_url: str
    license_name: str
    github_created_at: datetime
    github_pushed_at: datetime
    rank: int


class TopRepoDTO(BaseModel):
    """Top repository response — includes current repo metadata and window star context.

    Returned by ``GET /dashboard/top-repos`` and ``GET /dashboard/top-starred-repos``.
    """

    model_config = ConfigDict(frozen=True)

    repo: RepoMetadataDTO
    star_count_in_window: int = Field(..., ge=0)
    star_delta: int = Field(default=0, description="Star gain vs prior period.")


class TrendingRepoDTO(BaseModel):
    """Trending repository — ranked by recent star activity velocity.

    Returned by ``GET /dashboard/trending``.
    """

    model_config = ConfigDict(frozen=True)

    repo: RepoMetadataDTO
    star_count_in_window: int = Field(..., ge=0)
    growth_rank: int = Field(..., ge=1)


class TopicBreakdownDTO(BaseModel):
    """Event counts grouped by a single GitHub topic tag.

    Returned by ``GET /dashboard/topic-breakdown``.
    """

    model_config = ConfigDict(frozen=True)

    topic: str
    event_count: int = Field(..., ge=0)
    repo_count: int = Field(..., ge=0)


class LanguageBreakdownDTO(BaseModel):
    """Event counts grouped by primary programming language.

    Returned by ``GET /dashboard/language-breakdown``.
    """

    model_config = ConfigDict(frozen=True)

    language: str
    event_count: int = Field(..., ge=0)
    repo_count: int = Field(..., ge=0)


class RepoTimeseriesPointDTO(BaseModel):
    """Single day data point in a repo time-series chart.

    Returned by ``GET /dashboard/repo-timeseries``.
    """

    model_config = ConfigDict(frozen=True)

    event_date: date
    star_count: int = Field(..., ge=0)
    total_events: int = Field(..., ge=0)


class CategorySummaryDTO(BaseModel):
    """Aggregate statistics for a single AI category.

    Returned by ``GET /dashboard/category-summary``.
    """

    model_config = ConfigDict(frozen=True)

    category: str
    repo_count: int = Field(..., ge=0)
    total_stars: int = Field(..., ge=0)
    top_repo_name: str
    top_repo_stars: int = Field(..., ge=0)
    weekly_star_delta: int = Field(..., ge=0)


class ShockMoverDTO(BaseModel):
    """Repository mover surfaced from the current market window."""

    model_config = ConfigDict(frozen=True)

    repo: RepoMetadataDTO
    star_count_in_window: int = Field(..., ge=0)
    previous_star_count_in_window: int = Field(..., ge=0)
    unique_actors_in_window: int = Field(..., ge=0)
    weekly_percent_gain: float = Field(..., ge=0.0)
    window_over_window_ratio: float = Field(..., ge=0.0)
    rank: int = Field(..., ge=1)


class ShockMoversResponseDTO(BaseModel):
    """Combined absolute and percentage-based market movers."""

    model_config = ConfigDict(frozen=True)

    window_days: int = Field(..., ge=1, le=365)
    absolute_movers: list[ShockMoverDTO]
    percentage_movers: list[ShockMoverDTO]


class TopicRotationDTO(BaseModel):
    """Topic-level shift between the current and prior windows."""

    model_config = ConfigDict(frozen=True)

    topic: str
    current_star_count: int = Field(..., ge=0)
    previous_star_count: int = Field(..., ge=0)
    star_delta: int
    repo_count: int = Field(..., ge=0)
    rank: int = Field(..., ge=1)


class NewsHeadlineDTO(BaseModel):
    """One external headline returned by the news radar."""

    model_config = ConfigDict(frozen=True)

    title: str
    url: str
    source: str
    snippet: str
    engine: str | None = None


class RepoNewsRadarDTO(BaseModel):
    """External news bundle for one repository surfaced by the dashboard."""

    model_config = ConfigDict(frozen=True)

    repo_full_name: str
    category: str
    star_count_in_window: int = Field(..., ge=0)
    weekly_percent_gain: float = Field(..., ge=0.0)
    headlines: list[NewsHeadlineDTO]


class NewsRadarResponseDTO(BaseModel):
    """Top-level response for the external news radar block."""

    model_config = ConfigDict(frozen=True)

    window_days: int = Field(..., ge=1, le=365)
    repos: list[RepoNewsRadarDTO]
