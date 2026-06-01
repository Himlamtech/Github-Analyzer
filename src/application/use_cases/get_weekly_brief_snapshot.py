"""Curated backend snapshot for the weekly brief page."""

from __future__ import annotations

from datetime import UTC, datetime

from src.application.dtos.intelligence_dto import (
    WeeklyBriefAuthorDTO,
    WeeklyBriefChartPointDTO,
    WeeklyBriefPillarDTO,
    WeeklyBriefRegionDTO,
    WeeklyBriefSnapshotDTO,
)


class GetWeeklyBriefSnapshotUseCase:
    """Return the current curated weekly brief snapshot."""

    def execute(self) -> WeeklyBriefSnapshotDTO:
        return WeeklyBriefSnapshotDTO(
            brief_id="weekly-signal-vol-14",
            published_at=datetime.now(tz=UTC),
            title="The Weekly Signal: AI Market Intelligence Briefing",
            subtitle=(
                "Vol. 14 // Curated analysis linking low-level code commits, attention "
                "rotations, and capital structures in the cognitive ecosystem."
            ),
            pillars=[
                WeeklyBriefPillarDTO(
                    pillar_number="01",
                    title="The Great Decoupling of Orchestration Systems",
                    description=(
                        "We are witnessing a structural migration away from monolithic RAG "
                        "frameworks toward compact, event-driven state models."
                    ),
                ),
                WeeklyBriefPillarDTO(
                    pillar_number="02",
                    title="Latency Budgets Convert Entirely to Logic Budgets",
                    description=(
                        "Engineers are willing to spend more internal reasoning loops per "
                        "response, prioritizing accuracy over speed."
                    ),
                ),
                WeeklyBriefPillarDTO(
                    pillar_number="03",
                    title="Hardware-Native Acoustic Channels Form Ecosystem Moats",
                    description=(
                        "Direct auditory token streaming creates sticky software moats and "
                        "accelerates real-time interface ecosystems."
                    ),
                ),
            ],
            summary_chart_data=[
                WeeklyBriefChartPointDTO(period="Q1 2024", standard_rag=62, agentic_loops=14),
                WeeklyBriefChartPointDTO(period="Q2 2024", standard_rag=45, agentic_loops=38),
                WeeklyBriefChartPointDTO(period="Q3 2025", standard_rag=24, agentic_loops=64),
            ],
            evidence_spotlight_title="REPOSITORIES OUTBREAK RECORD",
            evidence_spotlight_body=(
                "In this briefing, the highlighted browser-use system provides direct "
                "evidence. Commits increased +412% QoQ representing active automation breakouts."
            ),
            evidence_spotlight_badge="Confirmed: Extreme durable breakout index",
            regional_indicators=[
                WeeklyBriefRegionDTO(
                    region="North America",
                    status="Stable",
                    active_percentage=68,
                ),
                WeeklyBriefRegionDTO(
                    region="European Union",
                    status="Slight lag",
                    active_percentage=42,
                ),
                WeeklyBriefRegionDTO(
                    region="APAC Region",
                    status="Fast accelerating",
                    active_percentage=84,
                ),
            ],
            authors=[
                WeeklyBriefAuthorDTO(
                    initials="AV",
                    name="Dr. Alistair Vance",
                    role="Director of Macro Strategy",
                ),
                WeeklyBriefAuthorDTO(
                    initials="SL",
                    name="Sasha Lindqvist",
                    role="Lead Telemetry Engineer",
                ),
            ],
            disclaimer=(
                "All assessments made are research opinions compiled from public stream "
                "metadata and proprietary causation indicators. Past velocity does not "
                "guarantee future momentum curves."
            ),
        )
