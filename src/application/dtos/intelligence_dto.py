"""DTOs for intelligence-focused API contracts."""

from __future__ import annotations

from datetime import datetime  # noqa: TC003

from pydantic import BaseModel, ConfigDict, Field

from src.application.dtos.repo_metadata_dto import RepoMetadataDTO  # noqa: TC001


class BreakoutRepositoryDTO(BaseModel):
    """Repository breakout intelligence returned by ``GET /intelligence/breakout``."""

    model_config = ConfigDict(frozen=True)

    repo: RepoMetadataDTO
    breakout_score: float = Field(..., ge=0.0, le=100.0)
    durability_score: float = Field(..., ge=0.0, le=100.0)
    hype_risk_score: float = Field(..., ge=0.0, le=100.0)
    confidence_score: float = Field(..., ge=0.0, le=100.0)
    star_gain_7d: int = Field(..., ge=0)
    unique_actors_7d: int = Field(..., ge=0)
    event_count_7d: int = Field(..., ge=0)
    star_gain_vs_previous_window: int
    explanation_trace: list[str]
    last_computed_at: datetime


class RotationCategoryDTO(BaseModel):
    """Category-level ecosystem rotation intelligence."""

    model_config = ConfigDict(frozen=True)

    category: str
    current_attention_score: float = Field(..., ge=0.0)
    previous_attention_score: float = Field(..., ge=0.0)
    attention_delta: float
    repo_count: int = Field(..., ge=0)
    top_repos: list[str]
    top_topics: list[str]
    confidence_score: float = Field(..., ge=0.0, le=100.0)
    rotation_drivers: list[str]
    last_computed_at: datetime


class RadarWinnerDTO(BaseModel):
    """Short winner or warning summary for the framework radar."""

    model_config = ConfigDict(frozen=True)

    title: str
    summary: str


class FrameworkRadarItemDTO(BaseModel):
    """Single framework item rendered on the competitive radar."""

    model_config = ConfigDict(frozen=True)

    framework_id: str
    framework_name: str
    velocity_score: float = Field(..., ge=0.0, le=1.0)
    commercial_readiness_score: float = Field(..., ge=0.0, le=1.0)
    contributor_energy_score: int = Field(..., ge=0, le=100)
    market_footprint: str
    strategic_insight_summary: str


class FrameworkRadarSnapshotDTO(BaseModel):
    """Curated backend snapshot for the competitive radar page."""

    model_config = ConfigDict(frozen=True)

    generated_at: datetime
    frameworks: list[FrameworkRadarItemDTO]
    winners: list[RadarWinnerDTO]
    warnings: list[RadarWinnerDTO]


class WeeklyBriefPillarDTO(BaseModel):
    """Single pillar in the weekly intelligence brief."""

    model_config = ConfigDict(frozen=True)

    pillar_number: str
    title: str
    description: str


class WeeklyBriefChartPointDTO(BaseModel):
    """Comparative chart point for the weekly brief."""

    model_config = ConfigDict(frozen=True)

    period: str
    standard_rag: int = Field(..., ge=0)
    agentic_loops: int = Field(..., ge=0)


class WeeklyBriefRegionDTO(BaseModel):
    """Regional adoption indicator rendered in the weekly brief."""

    model_config = ConfigDict(frozen=True)

    region: str
    status: str
    active_percentage: int = Field(..., ge=0, le=100)


class WeeklyBriefAuthorDTO(BaseModel):
    """Author metadata for the weekly brief."""

    model_config = ConfigDict(frozen=True)

    initials: str
    name: str
    role: str


class WeeklyBriefSnapshotDTO(BaseModel):
    """Curated backend snapshot for the weekly brief page."""

    model_config = ConfigDict(frozen=True)

    brief_id: str
    published_at: datetime
    title: str
    subtitle: str
    pillars: list[WeeklyBriefPillarDTO]
    summary_chart_data: list[WeeklyBriefChartPointDTO]
    evidence_spotlight_title: str
    evidence_spotlight_body: str
    evidence_spotlight_badge: str
    regional_indicators: list[WeeklyBriefRegionDTO]
    authors: list[WeeklyBriefAuthorDTO]
    disclaimer: str


class NewsImpactCurvePointDTO(BaseModel):
    """Single point on the news-to-code impact curve."""

    model_config = ConfigDict(frozen=True)

    time_bucket: str
    value: int = Field(..., ge=0)


class NewsImpactEventDTO(BaseModel):
    """Curated news-to-code impact event returned by the intelligence API."""

    model_config = ConfigDict(frozen=True)

    event_id: str
    source: str
    headline: str
    published_at: datetime
    provider: str
    event_type: str
    linked_entities: list[str]
    linked_categories: list[str]
    causality_score: float = Field(..., ge=0.0, le=100.0)
    lag_hours: float = Field(..., ge=0.0)
    impact_summary: str
    impact_curve: list[NewsImpactCurvePointDTO]
    top_impacted_repos: list[str]
    explanation_trace: list[str]
    last_computed_at: datetime
