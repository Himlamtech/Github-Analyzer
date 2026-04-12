"""Use case for grounded repository comparison."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal, Protocol

import structlog

from university.github.src.application.dtos.ai_repo_compare_dto import (
    RepoCompareMetricDTO,
    RepoCompareResponseDTO,
)
from university.github.src.domain.exceptions import GenerationServiceError, ValidationError

if TYPE_CHECKING:
    from university.github.src.application.dtos.ai_repo_brief_dto import RepoBriefContextDTO

logger = structlog.get_logger(__name__)

_SYSTEM_PROMPT = """
You are a grounded GitHub repository analyst.
Compare repositories using only the supplied metadata and metrics.
Be concise, analytical, and avoid hype.
"""

_COMPARE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "headline": {"type": "string"},
        "summary": {"type": "string"},
        "overall_winner": {
            "type": "string",
            "enum": ["base", "compare", "tie"],
        },
        "key_differences": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 2,
            "maxItems": 4,
        },
        "when_to_choose_base": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1,
            "maxItems": 3,
        },
        "when_to_choose_compare": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1,
            "maxItems": 3,
        },
    },
    "required": [
        "headline",
        "summary",
        "overall_winner",
        "key_differences",
        "when_to_choose_base",
        "when_to_choose_compare",
    ],
}


class RepoInsightContextProviderProtocol(Protocol):
    """Storage-backed provider for repository context."""

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


class GenerateRepoCompareUseCase:
    """Generate a grounded comparison between two repositories."""

    def __init__(
        self,
        context_provider: RepoInsightContextProviderProtocol,
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
        base_repo_name: str,
        compare_repo_name: str,
        days: int,
    ) -> RepoCompareResponseDTO:
        """Return a structured comparison between two repositories."""
        if base_repo_name == compare_repo_name:
            raise ValidationError("Comparison requires two distinct repositories.")

        base_context = await self._context_provider.get_repo_brief_context(
            repo_name=base_repo_name,
            days=days,
        )
        compare_context = await self._context_provider.get_repo_brief_context(
            repo_name=compare_repo_name,
            days=days,
        )
        generated = await self._maybe_generate_model_compare(base_context, compare_context)
        if generated is None:
            return _build_template_compare(base_context, compare_context)
        return _build_model_compare(base_context, compare_context, generated)

    async def _maybe_generate_model_compare(
        self,
        base_context: RepoBriefContextDTO,
        compare_context: RepoBriefContextDTO,
    ) -> dict[str, Any] | None:
        if not self._llm_enabled or self._generation_service is None:
            return None

        prompt = _build_prompt(base_context, compare_context)
        try:
            generated = await self._generation_service.generate_json(
                prompt=prompt,
                system_prompt=_SYSTEM_PROMPT.strip(),
                schema=_COMPARE_SCHEMA,
            )
        except GenerationServiceError as exc:
            logger.warning(
                "ai_repo_compare.generation_unavailable",
                base_repo=base_context.repo.repo_full_name,
                compare_repo=compare_context.repo.repo_full_name,
                error=str(exc),
            )
            return None

        if not _generated_compare_is_valid(generated):
            logger.warning(
                "ai_repo_compare.invalid_generation_payload",
                base_repo=base_context.repo.repo_full_name,
                compare_repo=compare_context.repo.repo_full_name,
            )
            return None
        return generated


def _build_prompt(
    base_context: RepoBriefContextDTO,
    compare_context: RepoBriefContextDTO,
) -> str:
    return f"""
Compare these two repositories for a product intelligence dashboard.

Base repo:
- name: {base_context.repo.repo_full_name}
- category: {base_context.repo.category}
- language: {base_context.repo.primary_language or "unknown"}
- description: {base_context.repo.description or "n/a"}
- topics: {", ".join(base_context.repo.topics) or "n/a"}
- total stars: {base_context.repo.stargazers_count}
- stars in {base_context.window_days}d: {base_context.star_count_in_window}
- total events in {base_context.window_days}d: {base_context.total_events_in_window}
- unique actors in {base_context.window_days}d: {base_context.unique_actors_in_window}
- forks: {base_context.repo.forks_count}

Compare repo:
- name: {compare_context.repo.repo_full_name}
- category: {compare_context.repo.category}
- language: {compare_context.repo.primary_language or "unknown"}
- description: {compare_context.repo.description or "n/a"}
- topics: {", ".join(compare_context.repo.topics) or "n/a"}
- total stars: {compare_context.repo.stargazers_count}
- stars in {compare_context.window_days}d: {compare_context.star_count_in_window}
- total events in {compare_context.window_days}d: {compare_context.total_events_in_window}
- unique actors in {compare_context.window_days}d: {compare_context.unique_actors_in_window}
- forks: {compare_context.repo.forks_count}

Write a compact comparison:
- identify the stronger repo overall in this window, or tie
- state the clearest tradeoffs
- give separate guidance on when to choose each repo
- use only the supplied facts
""".strip()


def _generated_compare_is_valid(payload: dict[str, Any]) -> bool:
    headline = payload.get("headline")
    summary = payload.get("summary")
    overall_winner = payload.get("overall_winner")
    key_differences = payload.get("key_differences")
    when_to_choose_base = payload.get("when_to_choose_base")
    when_to_choose_compare = payload.get("when_to_choose_compare")
    return (
        isinstance(headline, str)
        and isinstance(summary, str)
        and overall_winner in {"base", "compare", "tie"}
        and isinstance(key_differences, list)
        and all(isinstance(item, str) for item in key_differences)
        and isinstance(when_to_choose_base, list)
        and all(isinstance(item, str) for item in when_to_choose_base)
        and isinstance(when_to_choose_compare, list)
        and all(isinstance(item, str) for item in when_to_choose_compare)
    )


def _build_model_compare(
    base_context: RepoBriefContextDTO,
    compare_context: RepoBriefContextDTO,
    payload: dict[str, Any],
) -> RepoCompareResponseDTO:
    return RepoCompareResponseDTO(
        base_repo=base_context.repo,
        compare_repo=compare_context.repo,
        window_days=base_context.window_days,
        retrieval_mode="model",
        overall_winner=payload["overall_winner"],
        headline=str(payload["headline"]).strip(),
        summary=str(payload["summary"]).strip(),
        key_differences=[str(item).strip() for item in payload["key_differences"]][:4],
        when_to_choose_base=[str(item).strip() for item in payload["when_to_choose_base"]][:3],
        when_to_choose_compare=[str(item).strip() for item in payload["when_to_choose_compare"]][
            :3
        ],
        metric_snapshot=_metric_snapshot(base_context, compare_context),
    )


def _build_template_compare(
    base_context: RepoBriefContextDTO,
    compare_context: RepoBriefContextDTO,
) -> RepoCompareResponseDTO:
    metric_snapshot = _metric_snapshot(base_context, compare_context)
    overall_winner = _overall_winner(metric_snapshot)
    headline = _headline(base_context, compare_context, overall_winner)
    summary = _summary(base_context, compare_context, overall_winner)

    return RepoCompareResponseDTO(
        base_repo=base_context.repo,
        compare_repo=compare_context.repo,
        window_days=base_context.window_days,
        retrieval_mode="template",
        overall_winner=overall_winner,
        headline=headline,
        summary=summary,
        key_differences=_key_differences(base_context, compare_context, metric_snapshot),
        when_to_choose_base=_when_to_choose(base_context, compare_context, side="base"),
        when_to_choose_compare=_when_to_choose(
            base_context,
            compare_context,
            side="compare",
        ),
        metric_snapshot=metric_snapshot,
    )


def _metric_snapshot(
    base_context: RepoBriefContextDTO,
    compare_context: RepoBriefContextDTO,
) -> list[RepoCompareMetricDTO]:
    metrics = [
        (
            "total_stars",
            "Total Stars",
            base_context.repo.stargazers_count,
            compare_context.repo.stargazers_count,
        ),
        (
            "window_stars",
            f"Stars ({base_context.window_days}d)",
            base_context.star_count_in_window,
            compare_context.star_count_in_window,
        ),
        (
            "events",
            f"Events ({base_context.window_days}d)",
            base_context.total_events_in_window,
            compare_context.total_events_in_window,
        ),
        (
            "actors",
            f"Unique Actors ({base_context.window_days}d)",
            base_context.unique_actors_in_window,
            compare_context.unique_actors_in_window,
        ),
        (
            "forks",
            "Forks",
            base_context.repo.forks_count,
            compare_context.repo.forks_count,
        ),
    ]
    return [
        RepoCompareMetricDTO(
            key=key,
            label=label,
            base_value=base_value,
            compare_value=compare_value,
            winner=_winner(base_value, compare_value),
        )
        for key, label, base_value, compare_value in metrics
    ]


def _winner(base_value: int, compare_value: int) -> Literal["base", "compare", "tie"]:
    if base_value == compare_value:
        return "tie"
    return "base" if base_value > compare_value else "compare"


def _overall_winner(
    metrics: list[RepoCompareMetricDTO],
) -> Literal["base", "compare", "tie"]:
    base_wins = sum(1 for metric in metrics if metric.winner == "base")
    compare_wins = sum(1 for metric in metrics if metric.winner == "compare")
    if abs(base_wins - compare_wins) <= 1:
        return "tie"
    return "base" if base_wins > compare_wins else "compare"


def _headline(
    base_context: RepoBriefContextDTO,
    compare_context: RepoBriefContextDTO,
    overall_winner: Literal["base", "compare", "tie"],
) -> str:
    if overall_winner == "tie":
        return (
            f"{base_context.repo.repo_full_name} and "
            f"{compare_context.repo.repo_full_name} trade off momentum and ecosystem depth."
        )
    winning_repo = (
        base_context.repo.repo_full_name
        if overall_winner == "base"
        else compare_context.repo.repo_full_name
    )
    return f"{winning_repo} has the stronger overall signal in the current window."


def _summary(
    base_context: RepoBriefContextDTO,
    compare_context: RepoBriefContextDTO,
    overall_winner: Literal["base", "compare", "tie"],
) -> str:
    if overall_winner == "tie":
        return (
            f"{base_context.repo.repo_full_name} and {compare_context.repo.repo_full_name} "
            f"look balanced overall: one leads in some metrics while the other holds "
            f"up on recent adoption or ecosystem breadth."
        )
    winning_context = base_context if overall_winner == "base" else compare_context
    other_context = compare_context if overall_winner == "base" else base_context
    return (
        f"{winning_context.repo.repo_full_name} currently leads with "
        f"{winning_context.star_count_in_window:,} stars and "
        f"{winning_context.unique_actors_in_window:,} active actors in the last "
        f"{winning_context.window_days} days, while {other_context.repo.repo_full_name} "
        f"still remains relevant on specialization or installed base."
    )


def _key_differences(
    base_context: RepoBriefContextDTO,
    compare_context: RepoBriefContextDTO,
    metrics: list[RepoCompareMetricDTO],
) -> list[str]:
    differences: list[str] = []
    for metric in metrics[:4]:
        if metric.winner == "tie":
            continue
        leader = (
            base_context.repo.repo_full_name
            if metric.winner == "base"
            else compare_context.repo.repo_full_name
        )
        differences.append(
            f"{leader} leads on {metric.label.lower()} "
            f"({metric.base_value:,} vs {metric.compare_value:,})."
        )
    if base_context.repo.category != compare_context.repo.category:
        differences.append(
            f"The pair spans different categories: {base_context.repo.category} vs "
            f"{compare_context.repo.category}."
        )
    return differences[:4]


def _when_to_choose(
    base_context: RepoBriefContextDTO,
    compare_context: RepoBriefContextDTO,
    *,
    side: Literal["base", "compare"],
) -> list[str]:
    primary = base_context if side == "base" else compare_context
    secondary = compare_context if side == "base" else base_context
    choices = [
        f"Choose {primary.repo.repo_full_name} when you want a "
        f"{primary.repo.category.lower()} repo in "
        f"{primary.repo.primary_language or 'its current stack'}.",
    ]
    if primary.star_count_in_window >= secondary.star_count_in_window:
        choices.append(
            f"It has the stronger recent star momentum in the last {primary.window_days} days."
        )
    if primary.unique_actors_in_window >= secondary.unique_actors_in_window:
        choices.append("It currently shows broader recent actor participation.")
    if primary.repo.forks_count >= secondary.repo.forks_count:
        choices.append("Its fork base suggests a broader builder ecosystem.")
    return choices[:3]
