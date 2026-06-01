"""Curated backend snapshot for the news impact page."""

from __future__ import annotations

from datetime import UTC, datetime

from src.application.dtos.intelligence_dto import (
    NewsImpactCurvePointDTO,
    NewsImpactEventDTO,
)


class GetNewsImpactSnapshotUseCase:
    """Return the current curated news-to-code impact snapshot."""

    def execute(self) -> list[NewsImpactEventDTO]:
        computed_at = datetime.now(tz=UTC)

        return [
            NewsImpactEventDTO(
                event_id="anthropic-computer-use-2024-10-22",
                source="curated_snapshot",
                headline=("Anthropic Launches Computer-Use API in Upgrade of Claude 3.5 Sonnet"),
                published_at=datetime(2024, 10, 22, 16, 0, tzinfo=UTC),
                provider="Anthropic",
                event_type="launch",
                linked_entities=["Claude 3.5 Sonnet", "Computer Use API", "browser-use"],
                linked_categories=["System Automation", "Coding Agents & Automation"],
                causality_score=92.0,
                lag_hours=12.0,
                impact_summary="+340% system-level Python package attention after launch.",
                impact_curve=[
                    NewsImpactCurvePointDTO(time_bucket="0h", value=12),
                    NewsImpactCurvePointDTO(time_bucket="2h", value=18),
                    NewsImpactCurvePointDTO(time_bucket="6h", value=45),
                    NewsImpactCurvePointDTO(time_bucket="12h", value=140),
                    NewsImpactCurvePointDTO(time_bucket="24h", value=280),
                    NewsImpactCurvePointDTO(time_bucket="48h", value=340),
                ],
                top_impacted_repos=[
                    "browser-use/browser-use",
                    "microsoft/playwright-mcp",
                    "huggingface/smolagents",
                ],
                explanation_trace=[
                    "Curated from official provider launch material.",
                    "GitHub telemetry shows accelerated automation repo activity within 12 hours.",
                ],
                last_computed_at=computed_at,
            ),
            NewsImpactEventDTO(
                event_id="openai-o1-2024-09-12",
                source="curated_snapshot",
                headline="OpenAI Releases o1 Series with Multi-Turn Reasoning Capabilities",
                published_at=datetime(2024, 9, 12, 17, 0, tzinfo=UTC),
                provider="OpenAI",
                event_type="launch",
                linked_entities=["o1-preview", "o1-mini", "reasoning agents"],
                linked_categories=["Reasoning Frameworks", "Coding Agents & Automation"],
                causality_score=88.0,
                lag_hours=3.0,
                impact_summary="-45% prompt-hack attention and +160% agent-loop experimentation.",
                impact_curve=[
                    NewsImpactCurvePointDTO(time_bucket="0h", value=95),
                    NewsImpactCurvePointDTO(time_bucket="4h", value=75),
                    NewsImpactCurvePointDTO(time_bucket="12h", value=50),
                    NewsImpactCurvePointDTO(time_bucket="24h", value=120),
                    NewsImpactCurvePointDTO(time_bucket="48h", value=180),
                    NewsImpactCurvePointDTO(time_bucket="72h", value=240),
                ],
                top_impacted_repos=[
                    "microsoft/autogen",
                    "crewAIInc/crewAI",
                    "langchain-ai/langgraph",
                ],
                explanation_trace=[
                    "Curated from official launch communication and internal repo review.",
                    (
                        "Reasoning-native model launches correlate with orchestration repo "
                        "acceleration."
                    ),
                ],
                last_computed_at=computed_at,
            ),
            NewsImpactEventDTO(
                event_id="gemini-native-audio-2024-08-05",
                source="curated_snapshot",
                headline="The Multi-Modal Native Era: Gemini 1.5 Pro Native Audio Understanding",
                published_at=datetime(2024, 8, 5, 15, 0, tzinfo=UTC),
                provider="Google AI",
                event_type="launch",
                linked_entities=["Gemini 1.5 Pro", "Native Audio", "WebRTC"],
                linked_categories=["Speech & Acoustic Layers", "Multimodal Interfaces"],
                causality_score=85.0,
                lag_hours=24.0,
                impact_summary="+180% WebRTC and low-level audio pipeline fork activity.",
                impact_curve=[
                    NewsImpactCurvePointDTO(time_bucket="0h", value=50),
                    NewsImpactCurvePointDTO(time_bucket="4h", value=62),
                    NewsImpactCurvePointDTO(time_bucket="8h", value=90),
                    NewsImpactCurvePointDTO(time_bucket="12h", value=110),
                    NewsImpactCurvePointDTO(time_bucket="24h", value=165),
                    NewsImpactCurvePointDTO(time_bucket="48h", value=180),
                ],
                top_impacted_repos=[
                    "livekit/agents",
                    "aiortc/aiortc",
                    "openai/openai-realtime-console",
                ],
                explanation_trace=[
                    "Curated from public multimodal release coverage.",
                    (
                        "Repo forks concentrated around audio transport and real-time "
                        "streaming layers."
                    ),
                ],
                last_computed_at=computed_at,
            ),
        ]
