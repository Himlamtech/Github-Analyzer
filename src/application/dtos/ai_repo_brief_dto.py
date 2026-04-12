"""DTOs for grounded AI repository brief responses."""

from __future__ import annotations

from datetime import date, datetime  # noqa: TC003
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from university.github.src.application.dtos.repo_metadata_dto import RepoMetadataDTO  # noqa: TC001


class RepoBriefActivityDTO(BaseModel):
    """One activity bucket contributing to the repo brief."""

    model_config = ConfigDict(frozen=True)

    event_type: str
    event_count: int = Field(..., ge=0)


class RepoBriefTimeseriesPointDTO(BaseModel):
    """Daily time-series point used to derive trend acceleration."""

    model_config = ConfigDict(frozen=True)

    event_date: date
    star_count: int = Field(..., ge=0)
    total_events: int = Field(..., ge=0)


class RepoBriefContextDTO(BaseModel):
    """Repository context assembled from storage before generation."""

    model_config = ConfigDict(frozen=True)

    repo: RepoMetadataDTO
    window_days: int = Field(..., ge=1)
    star_count_in_window: int = Field(..., ge=0)
    total_events_in_window: int = Field(..., ge=0)
    unique_actors_in_window: int = Field(..., ge=0)
    latest_event_at: datetime | None = None
    activity_breakdown: list[RepoBriefActivityDTO]
    timeseries: list[RepoBriefTimeseriesPointDTO]


class RepoBriefResponseDTO(BaseModel):
    """Final AI repo brief returned to the frontend."""

    model_config = ConfigDict(frozen=True)

    repo: RepoMetadataDTO
    window_days: int = Field(..., ge=1)
    retrieval_mode: Literal["template", "model"]
    trend_verdict: Literal["accelerating", "steady", "emerging", "quiet"]
    headline: str
    summary: str
    why_trending: str
    star_count_in_window: int = Field(..., ge=0)
    total_events_in_window: int = Field(..., ge=0)
    unique_actors_in_window: int = Field(..., ge=0)
    latest_event_at: datetime | None = None
    activity_breakdown: list[RepoBriefActivityDTO]
    key_signals: list[str]
    watchouts: list[str]
