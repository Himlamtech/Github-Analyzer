"""Versioned weekly brief snapshot and archive use cases."""

from __future__ import annotations

from datetime import UTC, datetime

from src.application.dtos.intelligence_dto import (
    WeeklyBriefArchiveEntryDTO,
    WeeklyBriefAuthorDTO,
    WeeklyBriefChartPointDTO,
    WeeklyBriefPillarDTO,
    WeeklyBriefRegionDTO,
    WeeklyBriefSnapshotDTO,
)


def _weekly_brief_archive() -> list[WeeklyBriefSnapshotDTO]:
    return [
        WeeklyBriefSnapshotDTO(
            brief_id="weekly-signal-vol-14",
            published_at=datetime(2026, 5, 30, 9, 0, tzinfo=UTC),
            title="The Weekly Signal: AI Market Intelligence Briefing",
            subtitle=(
                "Vol. 14 // Computed briefing linking breakout repositories, category "
                "rotation, and framework velocity signals."
            ),
            pillars=[
                WeeklyBriefPillarDTO(
                    pillar_number="01",
                    title="Agentic automation now outruns passive RAG growth",
                    description=(
                        "Breakout repositories increasingly cluster around browser, coding, "
                        "and workflow automation rather than document-only stacks."
                    ),
                ),
                WeeklyBriefPillarDTO(
                    pillar_number="02",
                    title="Framework velocity is fragmenting into specialized operator loops",
                    description=(
                        "The strongest open-source momentum is shifting toward focused execution "
                        "surfaces instead of all-in-one orchestration bundles."
                    ),
                ),
                WeeklyBriefPillarDTO(
                    pillar_number="03",
                    title="Official launch news is landing faster in repo telemetry",
                    description=(
                        "NewsImpact events now persist official sources and tie them to current "
                        "GitHub acceleration windows for quicker verification."
                    ),
                ),
            ],
            summary_chart_data=[
                WeeklyBriefChartPointDTO(period="Q4 2025", standard_rag=41, agentic_loops=46),
                WeeklyBriefChartPointDTO(period="Q1 2026", standard_rag=35, agentic_loops=59),
                WeeklyBriefChartPointDTO(period="Q2 2026", standard_rag=28, agentic_loops=72),
            ],
            evidence_spotlight_title="BREAKOUT MOMENTUM CONFIRMED",
            evidence_spotlight_body=(
                "Current leaderboards show browser and coding-agent repositories dominating "
                "attention gains, validating the shift toward operator-centric tooling."
            ),
            evidence_spotlight_badge="Live analytics + official source sync aligned",
            regional_indicators=[
                WeeklyBriefRegionDTO(
                    region="North America", status="Stable", active_percentage=71
                ),
                WeeklyBriefRegionDTO(
                    region="European Union", status="Re-accelerating", active_percentage=49
                ),
                WeeklyBriefRegionDTO(
                    region="APAC Region", status="Fast accelerating", active_percentage=82
                ),
            ],
            authors=[
                WeeklyBriefAuthorDTO(
                    initials="AI", name="Analyzer Intelligence", role="System Briefing"
                ),
            ],
            disclaimer=(
                "This weekly brief combines public GitHub telemetry with official external "
                "news ingestion. It is an operational snapshot, not investment advice."
            ),
        ),
        WeeklyBriefSnapshotDTO(
            brief_id="weekly-signal-vol-13",
            published_at=datetime(2026, 5, 23, 9, 0, tzinfo=UTC),
            title="The Weekly Signal: AI Market Intelligence Briefing",
            subtitle="Vol. 13 // Earlier transition week before official-source persistence.",
            pillars=[
                WeeklyBriefPillarDTO(
                    pillar_number="01",
                    title="Breakout scoring stabilized around GitHub telemetry",
                    description=(
                        "Server-side breakout intelligence replaced most client-derived "
                        "momentum logic."
                    ),
                ),
                WeeklyBriefPillarDTO(
                    pillar_number="02",
                    title="Rotation pages began moving away from raw topic strings",
                    description=(
                        "Category cards started consolidating into clearer AI ecosystem segments."
                    ),
                ),
                WeeklyBriefPillarDTO(
                    pillar_number="03",
                    title="NewsImpact readiness moved from concept to operable ingestion",
                    description=(
                        "Official source configuration and preview contracts were introduced "
                        "for phased rollout."
                    ),
                ),
            ],
            summary_chart_data=[
                WeeklyBriefChartPointDTO(period="Q3 2025", standard_rag=48, agentic_loops=33),
                WeeklyBriefChartPointDTO(period="Q4 2025", standard_rag=42, agentic_loops=45),
                WeeklyBriefChartPointDTO(period="Q1 2026", standard_rag=35, agentic_loops=58),
            ],
            evidence_spotlight_title="TRANSITION WEEK",
            evidence_spotlight_body=(
                "Core intelligence contracts were stabilized ahead of the external-source "
                "persistence rollout."
            ),
            evidence_spotlight_badge="Contract stabilization complete",
            regional_indicators=[
                WeeklyBriefRegionDTO(
                    region="North America", status="Stable", active_percentage=69
                ),
                WeeklyBriefRegionDTO(
                    region="European Union", status="Holding", active_percentage=44
                ),
                WeeklyBriefRegionDTO(
                    region="APAC Region", status="Accelerating", active_percentage=78
                ),
            ],
            authors=[
                WeeklyBriefAuthorDTO(
                    initials="AI", name="Analyzer Intelligence", role="System Briefing"
                ),
            ],
            disclaimer=(
                "Historical weekly brief entry retained for archive navigation and version "
                "traceability."
            ),
        ),
    ]


class GetWeeklyBriefSnapshotUseCase:
    """Return the latest versioned weekly brief snapshot."""

    def execute(self) -> WeeklyBriefSnapshotDTO:
        return _weekly_brief_archive()[0]


class ListWeeklyBriefArchiveUseCase:
    """Return archive metadata for historical weekly briefs."""

    def execute(self) -> list[WeeklyBriefArchiveEntryDTO]:
        return [
            WeeklyBriefArchiveEntryDTO(
                brief_id=item.brief_id,
                published_at=item.published_at,
                title=item.title,
                subtitle=item.subtitle,
            )
            for item in _weekly_brief_archive()
        ]
