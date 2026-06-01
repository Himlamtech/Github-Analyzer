"""Curated backend snapshot for the framework radar page."""

from __future__ import annotations

from datetime import UTC, datetime

from src.application.dtos.intelligence_dto import (
    FrameworkRadarItemDTO,
    FrameworkRadarSnapshotDTO,
    RadarWinnerDTO,
)


class GetFrameworkRadarSnapshotUseCase:
    """Return the current curated framework radar snapshot."""

    def execute(self) -> FrameworkRadarSnapshotDTO:
        frameworks = [
            FrameworkRadarItemDTO(
                framework_id="langchain",
                framework_name="LangChain",
                velocity_score=0.85,
                commercial_readiness_score=0.90,
                contributor_energy_score=72,
                market_footprint="Enterprise Standard",
                strategic_insight_summary=(
                    "Maintains dominant total volume but suffers high friction. Commits "
                    "have slowed 18% QoQ. Developers are reverting to bare-metal solutions."
                ),
            ),
            FrameworkRadarItemDTO(
                framework_id="crewai",
                framework_name="CrewAI",
                velocity_score=0.25,
                commercial_readiness_score=0.68,
                contributor_energy_score=95,
                market_footprint="Emerging & Experimental",
                strategic_insight_summary=(
                    "Vibrant breakout momentum. Contributor density increased 340% in "
                    "180 days. Dominating conversational agent loops."
                ),
            ),
            FrameworkRadarItemDTO(
                framework_id="autogen",
                framework_name="AutoGen",
                velocity_score=0.48,
                commercial_readiness_score=0.55,
                contributor_energy_score=78,
                market_footprint="Emerging & Experimental",
                strategic_insight_summary=(
                    "Strong academic support from Microsoft. Highly capable for "
                    "sophisticated state-based graphs, but lacks easy deployment pathways."
                ),
            ),
            FrameworkRadarItemDTO(
                framework_id="llamaindex",
                framework_name="LlamaIndex",
                velocity_score=0.60,
                commercial_readiness_score=0.82,
                contributor_energy_score=84,
                market_footprint="Enterprise Standard",
                strategic_insight_summary=(
                    "Solidifying its defensive hold as a definitive vector pipeline "
                    "platform while branching into data orchestration workflows."
                ),
            ),
            FrameworkRadarItemDTO(
                framework_id="semantic-kernel",
                framework_name="Semantic Kernel",
                velocity_score=0.70,
                commercial_readiness_score=0.80,
                contributor_energy_score=61,
                market_footprint="Enterprise Standard",
                strategic_insight_summary=(
                    "Dominates standard corporate .NET deployments, but sees minimal "
                    "open-source experimental startup capture."
                ),
            ),
        ]

        winners = [
            RadarWinnerDTO(
                title="CrewAI Ecosystem",
                summary="Rising +340% contributors with strong breakout momentum.",
            ),
            RadarWinnerDTO(
                title="LlamaIndex Vector Orchestration",
                summary="Solid enterprise caching and durable workflow expansion.",
            ),
        ]
        warnings = [
            RadarWinnerDTO(
                title="LangChain Monolith",
                summary="Commits slowed down 18% QoQ as developers move toward leaner stacks.",
            ),
            RadarWinnerDTO(
                title="Prompt Engineering Repos",
                summary=(
                    "Latent-token reasoning reduces demand for brittle prompt-hack repositories."
                ),
            ),
        ]

        return FrameworkRadarSnapshotDTO(
            generated_at=datetime.now(tz=UTC),
            frameworks=frameworks,
            winners=winners,
            warnings=warnings,
        )
