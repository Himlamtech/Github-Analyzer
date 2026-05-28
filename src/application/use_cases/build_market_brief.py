"""Use case for generating a grounded market brief."""

from __future__ import annotations

from typing import Protocol

import structlog

from src.application.dtos.ai_market_brief_dto import (
    MarketBreakoutRepoDTO,
    MarketBriefContextDTO,
    MarketBriefResponseDTO,
    MarketCategoryMoverDTO,
    MarketTopicShiftDTO,
)

logger = structlog.get_logger(__name__)


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


class BuildMarketBriefUseCase:
    """Generate a grounded AI market brief for the current time window."""

    def __init__(
        self,
        context_provider: MarketBriefContextProviderProtocol,
    ) -> None:
        self._context_provider = context_provider

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
        return _build_template_brief(context)


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
