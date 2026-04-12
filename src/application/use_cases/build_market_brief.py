"""Use case for generating a grounded market brief."""

from __future__ import annotations

from typing import Any, Protocol

import structlog

from src.application.dtos.ai_market_brief_dto import (
    MarketBreakoutRepoDTO,
    MarketBriefContextDTO,
    MarketBriefResponseDTO,
    MarketCategoryMoverDTO,
    MarketTopicShiftDTO,
)
from src.domain.exceptions import GenerationServiceError

logger = structlog.get_logger(__name__)

_SYSTEM_PROMPT = """
You are a grounded GitHub AI market analyst.
Write short, evidence-backed market briefings from structured metrics only.
Do not invent repos, metrics, trends, or causes not present in the prompt.
"""

_MARKET_BRIEF_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "headline": {"type": "string"},
        "summary": {"type": "string"},
        "key_takeaways": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 3,
            "maxItems": 5,
        },
        "watchouts": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1,
            "maxItems": 3,
        },
    },
    "required": ["headline", "summary", "key_takeaways", "watchouts"],
}


class MarketBriefContextProviderProtocol(Protocol):
    """Storage-backed provider for market brief context."""

    async def get_market_brief_context(
        self,
        *,
        days: int,
        breakout_limit: int,
        category_limit: int,
        topic_limit: int,
    ) -> MarketBriefContextDTO: ...


class StructuredGenerationServiceProtocol(Protocol):
    """LLM-backed JSON generation boundary."""

    async def generate_json(
        self,
        *,
        prompt: str,
        system_prompt: str,
        schema: dict[str, Any],
    ) -> dict[str, Any]: ...


class BuildMarketBriefUseCase:
    """Generate a grounded AI market brief for the current time window."""

    def __init__(
        self,
        context_provider: MarketBriefContextProviderProtocol,
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
        days: int,
        breakout_limit: int,
        category_limit: int,
        topic_limit: int,
    ) -> MarketBriefResponseDTO:
        """Return a structured market brief for the selected window."""
        context = await self._context_provider.get_market_brief_context(
            days=days,
            breakout_limit=breakout_limit,
            category_limit=category_limit,
            topic_limit=topic_limit,
        )
        generated = await self._maybe_generate_model_brief(context)
        if generated is None:
            return _build_template_brief(context)
        return _build_model_brief(context, generated)

    async def _maybe_generate_model_brief(
        self,
        context: MarketBriefContextDTO,
    ) -> dict[str, Any] | None:
        if not self._llm_enabled or self._generation_service is None:
            return None
        prompt = _build_prompt(context)
        try:
            generated = await self._generation_service.generate_json(
                prompt=prompt,
                system_prompt=_SYSTEM_PROMPT.strip(),
                schema=_MARKET_BRIEF_SCHEMA,
            )
        except GenerationServiceError as exc:
            logger.warning("ai_market_brief.generation_unavailable", error=str(exc))
            return None
        if not _generated_market_brief_is_valid(generated):
            logger.warning("ai_market_brief.invalid_generation_payload")
            return None
        return generated


def _build_prompt(context: MarketBriefContextDTO) -> str:
    breakout_lines = (
        "\n".join(
            (
                f"- {item.repo.repo_full_name}: +{item.star_count_in_window} stars, "
                f"{item.total_events_in_window} events, {item.unique_actors_in_window} actors, "
                f"momentum={item.momentum_score:.4f}"
            )
            for item in context.breakout_repos
        )
        or "- none"
    )
    category_lines = (
        "\n".join(
            (
                f"- {item.category}: {item.total_stars_in_window} stars, "
                f"{item.total_events_in_window} events, {item.active_repo_count} active repos, "
                f"leader={item.leader_repo_name}"
            )
            for item in context.category_movers
        )
        or "- none"
    )
    topic_lines = (
        "\n".join(
            f"- {item.topic}: {item.star_count_in_window} stars across {item.repo_count} repos"
            for item in context.topic_shifts
        )
        or "- none"
    )
    return f"""
Window days: {context.window_days}
Generated at: {context.generated_at.isoformat()}

Breakout repos:
{breakout_lines}

Category movers:
{category_lines}

Topic shifts:
{topic_lines}

Write a tight product-market brief for a dashboard.
Requirements:
- sound analytical, not promotional
- cite concrete repos or categories when relevant
- focus on where attention is concentrating
- keep each bullet compact
""".strip()


def _generated_market_brief_is_valid(payload: dict[str, Any]) -> bool:
    headline = payload.get("headline")
    summary = payload.get("summary")
    key_takeaways = payload.get("key_takeaways")
    watchouts = payload.get("watchouts")
    return (
        isinstance(headline, str)
        and isinstance(summary, str)
        and isinstance(key_takeaways, list)
        and all(isinstance(item, str) for item in key_takeaways)
        and isinstance(watchouts, list)
        and all(isinstance(item, str) for item in watchouts)
    )


def _build_model_brief(
    context: MarketBriefContextDTO,
    payload: dict[str, Any],
) -> MarketBriefResponseDTO:
    return MarketBriefResponseDTO(
        window_days=context.window_days,
        generated_at=context.generated_at,
        retrieval_mode="model",
        headline=str(payload["headline"]).strip(),
        summary=str(payload["summary"]).strip(),
        key_takeaways=[str(item).strip() for item in payload["key_takeaways"]][:5],
        watchouts=[str(item).strip() for item in payload["watchouts"]][:3],
        breakout_repos=context.breakout_repos,
        category_movers=context.category_movers,
        topic_shifts=context.topic_shifts,
    )


def _build_template_brief(context: MarketBriefContextDTO) -> MarketBriefResponseDTO:
    top_breakout = context.breakout_repos[0] if context.breakout_repos else None
    top_category = context.category_movers[0] if context.category_movers else None
    top_topic = context.topic_shifts[0] if context.topic_shifts else None

    if top_breakout is None:
        headline = f"GitHub AI activity looks quiet across the last {context.window_days} days."
        summary = (
            "No breakout repositories met the current threshold, so the market brief is "
            "showing a low-signal window."
        )
        key_takeaways = [
            "Breakout activity is currently thin in the selected window.",
            "Category rotation is muted, so dashboard users should widen the date range.",
        ]
        watchouts = ["Sparse event volume limits confidence in short-window conclusions."]
    else:
        headline = (
            f"{top_breakout.repo.repo_full_name} leads the {context.window_days}d cycle "
            f"with +{top_breakout.star_count_in_window:,} stars."
        )
        summary = _build_template_summary(top_breakout, top_category, top_topic, context)
        key_takeaways = _build_key_takeaways(context, top_breakout, top_category, top_topic)
        watchouts = _build_watchouts(context, top_breakout, top_category)

    return MarketBriefResponseDTO(
        window_days=context.window_days,
        generated_at=context.generated_at,
        retrieval_mode="template",
        headline=headline,
        summary=summary,
        key_takeaways=key_takeaways[:5],
        watchouts=watchouts[:3],
        breakout_repos=context.breakout_repos,
        category_movers=context.category_movers,
        topic_shifts=context.topic_shifts,
    )


def _build_template_summary(
    top_breakout: MarketBreakoutRepoDTO,
    top_category: MarketCategoryMoverDTO | None,
    top_topic: MarketTopicShiftDTO | None,
    context: MarketBriefContextDTO,
) -> str:
    parts = [
        (
            f"{top_breakout.repo.repo_full_name} is the strongest breakout with "
            f"{top_breakout.total_events_in_window:,} total events and "
            f"{top_breakout.unique_actors_in_window:,} distinct actors."
        )
    ]
    if top_category is not None:
        parts.append(
            f"{top_category.category} is absorbing the most star flow, led by "
            f"{top_category.leader_repo_name}."
        )
    if top_topic is not None:
        parts.append(
            f"The hottest topic signal is {top_topic.topic}, appearing across "
            f"{top_topic.repo_count} active repositories."
        )
    if len(context.breakout_repos) > 1:
        parts.append(
            f"{len(context.breakout_repos)} breakout repos are strong enough to surface in this "
            "window, which suggests concentrated rather than broad-based momentum."
        )
    return " ".join(parts)


def _build_key_takeaways(
    context: MarketBriefContextDTO,
    top_breakout: MarketBreakoutRepoDTO,
    top_category: MarketCategoryMoverDTO | None,
    top_topic: MarketTopicShiftDTO | None,
) -> list[str]:
    takeaways = [
        (
            f"{top_breakout.repo.repo_full_name} leads on near-term attention with "
            f"+{top_breakout.star_count_in_window:,} stars and "
            f"{top_breakout.unique_actors_in_window:,} active actors."
        )
    ]
    if len(context.breakout_repos) > 1:
        runner_up = context.breakout_repos[1]
        takeaways.append(
            f"{runner_up.repo.repo_full_name} is the next breakout, indicating the field is not "
            "a single-repo story."
        )
    if top_category is not None:
        takeaways.append(
            f"{top_category.category} is the strongest category mover with "
            f"{top_category.total_stars_in_window:,} stars in the window."
        )
    if top_topic is not None:
        takeaways.append(
            f"{top_topic.topic} is the clearest topic shift, spanning {top_topic.repo_count} "
            "repositories."
        )
    return takeaways


def _build_watchouts(
    context: MarketBriefContextDTO,
    top_breakout: MarketBreakoutRepoDTO,
    top_category: MarketCategoryMoverDTO | None,
) -> list[str]:
    watchouts: list[str] = []
    total_breakout_stars = sum(item.star_count_in_window for item in context.breakout_repos)
    if total_breakout_stars > 0:
        top_share = top_breakout.star_count_in_window / total_breakout_stars
        if top_share >= 0.5:
            watchouts.append(
                "A single breakout repo is capturing more than half of the surfaced star flow."
            )
    if top_category is not None and top_category.share_of_window_stars >= 0.5:
        watchouts.append(
            f"{top_category.category} dominates the current window, so cross-category breadth is "
            "limited."
        )
    if len(context.topic_shifts) <= 1:
        watchouts.append("Topic breadth is narrow, so trend rotation is still early.")
    if not watchouts:
        watchouts.append(
            "Momentum is distributed enough that rankings may reshuffle quickly in the next run."
        )
    return watchouts
