"""Use case for grounded repository intelligence briefs."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal, Protocol

import structlog

from src.application.dtos.ai_repo_brief_dto import (
    RepoBriefActivityDTO,
    RepoBriefContextDTO,
    RepoBriefResponseDTO,
    RepoBriefTimeseriesPointDTO,
)
from src.domain.exceptions import GenerationServiceError

logger = structlog.get_logger(__name__)

_SYSTEM_PROMPT = """
You are a grounded GitHub repository analyst.
Write crisp, evidence-backed repo intelligence.
Use only the supplied metrics and metadata.
Do not invent facts, dates, or benchmarks.
"""

_BRIEF_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "headline": {"type": "string"},
        "summary": {"type": "string"},
        "why_trending": {"type": "string"},
        "trend_verdict": {
            "type": "string",
            "enum": ["accelerating", "steady", "emerging", "quiet"],
        },
        "key_signals": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 2,
            "maxItems": 4,
        },
        "watchouts": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1,
            "maxItems": 3,
        },
    },
    "required": [
        "headline",
        "summary",
        "why_trending",
        "trend_verdict",
        "key_signals",
        "watchouts",
    ],
}


class RepoBriefContextProviderProtocol(Protocol):
    """Storage-backed provider for repo intelligence context."""

    async def get_repo_brief_context(
        self,
        *,
        repo_name: str,
        days: int,
    ) -> RepoBriefContextDTO: ...


class StructuredGenerationServiceProtocol(Protocol):
    """LLM-backed JSON generation boundary."""

    async def generate_json(
        self,
        *,
        prompt: str,
        system_prompt: str,
        schema: dict[str, Any],
    ) -> dict[str, Any]: ...


class GenerateRepoBriefUseCase:
    """Generate an evidence-backed brief explaining why a repo matters now."""

    def __init__(
        self,
        context_provider: RepoBriefContextProviderProtocol,
        *,
        generation_service: StructuredGenerationServiceProtocol | None = None,
        llm_enabled: bool = True,
    ) -> None:
        self._context_provider = context_provider
        self._generation_service = generation_service
        self._llm_enabled = llm_enabled

    async def execute(
        self,
        *,
        repo_name: str,
        days: int,
    ) -> RepoBriefResponseDTO:
        """Return a structured repo brief for the requested repository."""
        context = await self._context_provider.get_repo_brief_context(
            repo_name=repo_name,
            days=days,
        )
        generated = await self._maybe_generate_model_brief(context)
        if generated is None:
            return _build_template_brief(context)
        return _build_model_brief(context, generated)

    async def _maybe_generate_model_brief(
        self,
        context: RepoBriefContextDTO,
    ) -> dict[str, Any] | None:
        if not self._llm_enabled or self._generation_service is None:
            return None
        prompt = _build_prompt(context)
        try:
            generated = await self._generation_service.generate_json(
                prompt=prompt,
                system_prompt=_SYSTEM_PROMPT.strip(),
                schema=_BRIEF_SCHEMA,
            )
        except GenerationServiceError as exc:
            logger.warning(
                "ai_repo_brief.generation_unavailable",
                repo=context.repo.repo_full_name,
                error=str(exc),
            )
            return None
        if not _generated_brief_is_valid(generated):
            logger.warning(
                "ai_repo_brief.invalid_generation_payload",
                repo=context.repo.repo_full_name,
            )
            return None
        return generated


def _build_prompt(context: RepoBriefContextDTO) -> str:
    dominant_events = (
        ", ".join(f"{item.event_type}:{item.event_count}" for item in context.activity_breakdown)
        or "none"
    )
    latest_event = context.latest_event_at.isoformat() if context.latest_event_at else "unknown"
    recent_star_rate, prior_star_rate = _half_window_star_rates(context.timeseries)
    return f"""
Repository: {context.repo.repo_full_name}
Category: {context.repo.category}
Primary language: {context.repo.primary_language or "unknown"}
Description: {context.repo.description or "n/a"}
Topics: {", ".join(context.repo.topics) or "n/a"}
Total stars: {context.repo.stargazers_count}
Forks: {context.repo.forks_count}
Open issues: {context.repo.open_issues_count}
Window days: {context.window_days}
Stars in window: {context.star_count_in_window}
Total events in window: {context.total_events_in_window}
Unique actors in window: {context.unique_actors_in_window}
Latest event at: {latest_event}
Dominant events: {dominant_events}
Recent half star rate: {recent_star_rate:.2f}
Prior half star rate: {prior_star_rate:.2f}

Write a concise repo brief for a product dashboard.
Requirements:
- sound analytical, not promotional
- mention concrete metrics
- explain whether the repo is accelerating, steady, emerging, or quiet
- keep each sentence compact
""".strip()


def _generated_brief_is_valid(payload: dict[str, Any]) -> bool:
    headline = payload.get("headline")
    summary = payload.get("summary")
    why_trending = payload.get("why_trending")
    trend_verdict = payload.get("trend_verdict")
    key_signals = payload.get("key_signals")
    watchouts = payload.get("watchouts")
    return (
        isinstance(headline, str)
        and isinstance(summary, str)
        and isinstance(why_trending, str)
        and trend_verdict in {"accelerating", "steady", "emerging", "quiet"}
        and isinstance(key_signals, list)
        and all(isinstance(item, str) for item in key_signals)
        and isinstance(watchouts, list)
        and all(isinstance(item, str) for item in watchouts)
    )


def _build_model_brief(
    context: RepoBriefContextDTO,
    payload: dict[str, Any],
) -> RepoBriefResponseDTO:
    return RepoBriefResponseDTO(
        repo=context.repo,
        window_days=context.window_days,
        retrieval_mode="model",
        trend_verdict=payload["trend_verdict"],
        headline=str(payload["headline"]).strip(),
        summary=str(payload["summary"]).strip(),
        why_trending=str(payload["why_trending"]).strip(),
        star_count_in_window=context.star_count_in_window,
        total_events_in_window=context.total_events_in_window,
        unique_actors_in_window=context.unique_actors_in_window,
        latest_event_at=context.latest_event_at,
        activity_breakdown=context.activity_breakdown,
        key_signals=[str(item).strip() for item in payload["key_signals"]][:4],
        watchouts=[str(item).strip() for item in payload["watchouts"]][:3],
    )


def _build_template_brief(context: RepoBriefContextDTO) -> RepoBriefResponseDTO:
    verdict = _trend_verdict(context)
    dominant = _dominant_event(context.activity_breakdown)
    language = context.repo.primary_language or "unknown stack"
    category = context.repo.category or "Other"
    last_push_age = _days_since(context.repo.github_pushed_at)

    headline = (
        f"{context.repo.repo_full_name} is {verdict} in {category.lower()} "
        f"with +{context.star_count_in_window:,} stars over {context.window_days}d."
    )
    summary = (
        f"{context.repo.repo_full_name} is a {category.lower()} repository in {language} "
        f"with {context.repo.stargazers_count:,} total stars, {context.total_events_in_window:,} "
        f"events, and {context.unique_actors_in_window:,} active actors in the last "
        f"{context.window_days} days."
    )
    why_trending = _why_trending_text(context, verdict, dominant)
    key_signals = _build_key_signals(context, dominant)
    watchouts = _build_watchouts(context, last_push_age)

    return RepoBriefResponseDTO(
        repo=context.repo,
        window_days=context.window_days,
        retrieval_mode="template",
        trend_verdict=verdict,
        headline=headline,
        summary=summary,
        why_trending=why_trending,
        star_count_in_window=context.star_count_in_window,
        total_events_in_window=context.total_events_in_window,
        unique_actors_in_window=context.unique_actors_in_window,
        latest_event_at=context.latest_event_at,
        activity_breakdown=context.activity_breakdown,
        key_signals=key_signals,
        watchouts=watchouts,
    )


def _trend_verdict(
    context: RepoBriefContextDTO,
) -> Literal["accelerating", "steady", "emerging", "quiet"]:
    recent_star_rate, prior_star_rate = _half_window_star_rates(context.timeseries)
    if context.star_count_in_window >= 250 and recent_star_rate >= max(prior_star_rate * 1.2, 5.0):
        return "accelerating"
    if context.star_count_in_window >= 100 or context.total_events_in_window >= 250:
        return "steady"
    if context.star_count_in_window > 0 or context.total_events_in_window >= 40:
        return "emerging"
    return "quiet"


def _half_window_star_rates(
    timeseries: list[RepoBriefTimeseriesPointDTO],
) -> tuple[float, float]:
    star_counts = [int(getattr(point, "star_count", 0)) for point in timeseries]
    if not star_counts:
        return 0.0, 0.0
    midpoint = max(len(star_counts) // 2, 1)
    prior = star_counts[:midpoint]
    recent = star_counts[midpoint:]
    prior_rate = (sum(prior) / len(prior)) if prior else 0.0
    recent_rate = (sum(recent) / len(recent)) if recent else float(sum(prior))
    return recent_rate, prior_rate


def _dominant_event(
    activity_breakdown: list[RepoBriefActivityDTO],
) -> RepoBriefActivityDTO | None:
    if not activity_breakdown:
        return None
    return max(activity_breakdown, key=lambda item: item.event_count)


def _why_trending_text(
    context: RepoBriefContextDTO,
    verdict: str,
    dominant: RepoBriefActivityDTO | None,
) -> str:
    recent_star_rate, prior_star_rate = _half_window_star_rates(context.timeseries)
    dominant_text = (
        f"{dominant.event_type} led activity with {dominant.event_count:,} events"
        if dominant is not None
        else "activity was spread across a small number of events"
    )
    if verdict == "accelerating":
        return (
            f"Momentum is accelerating because the repo added "
            f"{context.star_count_in_window:,} stars in {context.window_days}d and "
            f"the recent daily star rate ({recent_star_rate:.1f}) is "
            f"ahead of the prior half-window ({prior_star_rate:.1f}); {dominant_text}."
        )
    if verdict == "steady":
        return (
            f"The repo is sustaining attention with "
            f"{context.total_events_in_window:,} recent events "
            f"from {context.unique_actors_in_window:,} actors; {dominant_text}."
        )
    if verdict == "emerging":
        return (
            f"The signal is early but real: {context.star_count_in_window:,} stars and "
            f"{context.total_events_in_window:,} events appeared in the last "
            f"{context.window_days}d; "
            f"{dominant_text}."
        )
    return (
        f"Current activity is muted. The repo still has "
        f"{context.repo.stargazers_count:,} total stars, "
        f"but only {context.total_events_in_window:,} recent events were observed."
    )


def _build_key_signals(
    context: RepoBriefContextDTO,
    dominant: RepoBriefActivityDTO | None,
) -> list[str]:
    signals = [
        f"{context.repo.stargazers_count:,} total GitHub stars with "
        f"+{context.star_count_in_window:,} in the last {context.window_days}d.",
        f"{context.total_events_in_window:,} tracked events from "
        f"{context.unique_actors_in_window:,} unique actors in the current window.",
    ]
    if dominant is not None:
        signals.append(
            f"{dominant.event_type} is the dominant activity type at "
            f"{dominant.event_count:,} events."
        )
    if context.repo.primary_language:
        signals.append(f"Primary implementation language is {context.repo.primary_language}.")
    return signals[:4]


def _build_watchouts(
    context: RepoBriefContextDTO,
    last_push_age: int,
) -> list[str]:
    watchouts: list[str] = []
    if context.unique_actors_in_window < 20 and context.star_count_in_window > 0:
        watchouts.append(
            "Attention is rising faster than contributor breadth, so momentum may be audience-led."
        )
    if last_push_age > 90:
        watchouts.append(
            f"Latest GitHub push is {last_push_age} days old, so shipping cadence "
            "may lag attention."
        )
    if not context.repo.description:
        watchouts.append(
            "Repository metadata is sparse, which weakens downstream semantic understanding."
        )
    if context.total_events_in_window == 0:
        watchouts.append("No recent tracked events were observed in the selected window.")
    return watchouts[:3] or [
        "Current signal is mostly event-driven; deeper README and issue analysis is still pending."
    ]


def _days_since(timestamp: datetime) -> int:
    now = datetime.now(tz=UTC)
    return max((now - timestamp).days, 0)
