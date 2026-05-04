"""Use case for answering chat questions with grounded GitHub trend data."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, Literal, Protocol

import structlog

from src.application.dtos.ai_chat_dto import (
    AIChatEvidenceDTO,
    AIChatMessageDTO,
    AIChatResponseDTO,
)
from src.domain.exceptions import (
    AIInsightError,
    AISearchError,
    GenerationServiceError,
    ValidationError,
)

if TYPE_CHECKING:
    from src.application.dtos.ai_market_brief_dto import MarketBriefResponseDTO
    from src.application.dtos.ai_repo_brief_dto import RepoBriefResponseDTO
    from src.application.dtos.ai_search_dto import RepoSearchResponseDTO

logger = structlog.get_logger(__name__)

_REPO_PATTERN = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+")
_TOPIC_PATTERN = re.compile(r"\b(topic|topics|tag|tags|chu de|stack|cong nghe)\b", re.I)
_CATEGORY_PATTERN = re.compile(r"\b(category|categories|danh muc|nhom|phan khuc)\b", re.I)
_SEARCH_PATTERN = re.compile(
    r"\b(search|find|tim|tim kiem|goi y|repo ve|repositories about)\b",
    re.I,
)
_SYSTEM_PROMPT = """
You are a grounded GitHub AI data analyst.
Answer only from the provided evidence.
Do not invent repositories, star counts, categories, topics, or causes.
Keep the answer concise, useful, and direct.
"""

_CHAT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "answer": {"type": "string"},
        "follow_up_questions": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 2,
            "maxItems": 4,
        },
    },
    "required": ["answer", "follow_up_questions"],
}

Intent = Literal["market", "repo", "search", "mixed"]


class MarketBriefUseCaseProtocol(Protocol):
    """Subset of the market brief use case needed by the chat agent."""

    async def execute(
        self,
        *,
        days: int,
        breakout_limit: int,
        category_limit: int,
        topic_limit: int,
    ) -> MarketBriefResponseDTO: ...


class RepoBriefUseCaseProtocol(Protocol):
    """Subset of the repo brief use case needed by the chat agent."""

    async def execute(self, *, repo_name: str, days: int) -> RepoBriefResponseDTO: ...


class SearchUseCaseProtocol(Protocol):
    """Subset of the search use case needed by the chat agent."""

    async def execute(
        self,
        *,
        query: str,
        category: str | None,
        primary_language: str | None,
        min_stars: int,
        days: int,
        limit: int,
    ) -> RepoSearchResponseDTO: ...


class StructuredGenerationServiceProtocol(Protocol):
    """LLM-backed JSON generation boundary."""

    async def generate_json(
        self,
        *,
        prompt: str,
        system_prompt: str,
        schema: dict[str, Any],
    ) -> dict[str, Any]: ...


class AnswerGithubDataQuestionUseCase:
    """Answer natural-language GitHub trend questions with real project data."""

    def __init__(
        self,
        *,
        market_brief_use_case: MarketBriefUseCaseProtocol,
        repo_brief_use_case: RepoBriefUseCaseProtocol,
        search_use_case: SearchUseCaseProtocol,
        generation_service: StructuredGenerationServiceProtocol | None = None,
        llm_enabled: bool = True,
    ) -> None:
        self._market_brief_use_case = market_brief_use_case
        self._repo_brief_use_case = repo_brief_use_case
        self._search_use_case = search_use_case
        self._generation_service = generation_service
        self._llm_enabled = llm_enabled

    async def execute(
        self,
        *,
        question: str,
        days: int,
        history: list[AIChatMessageDTO] | None = None,
    ) -> AIChatResponseDTO:
        """Return a grounded chat answer and the data evidence used to produce it."""
        normalized_question = question.strip()
        if len(normalized_question) < 2:
            raise ValidationError("Chat question must contain at least 2 characters.")

        repo_name = _extract_repo_name(normalized_question)
        if repo_name is None and history:
            repo_name = _extract_repo_name_from_history(history)
        intent = _detect_intent(normalized_question, repo_name)
        tools_used: list[str] = []
        evidence: list[AIChatEvidenceDTO] = []

        market = await self._load_market_context(days)
        if market is not None:
            tools_used.append("market-brief")
            evidence.extend(_market_evidence(market, normalized_question))

        search = await self._load_search_context(normalized_question, days)
        if search is not None:
            tools_used.append("search")
            evidence.extend(_search_evidence(search))

        repo_brief: RepoBriefResponseDTO | None = None
        if repo_name is not None:
            repo_brief = await self._load_repo_context(repo_name, days)
            if repo_brief is not None:
                tools_used.append("repo-brief")
                evidence.extend(_repo_evidence(repo_brief))

        if not evidence:
            raise AIInsightError("No GitHub trend data was available for chat.")

        generated = await self._maybe_generate_answer(
            question=normalized_question,
            intent=intent,
            evidence=evidence,
        )
        if generated is not None:
            return AIChatResponseDTO(
                answer=generated["answer"],
                mode="model",
                intent=intent,
                tools_used=tools_used,
                evidence=evidence[:12],
                follow_up_questions=generated["follow_up_questions"],
            )

        return AIChatResponseDTO(
            answer=_build_template_answer(
                question=normalized_question,
                intent=intent,
                evidence=evidence,
                market=market,
                search=search,
                repo_brief=repo_brief,
            ),
            mode="template",
            intent=intent,
            tools_used=tools_used,
            evidence=evidence[:12],
            follow_up_questions=_follow_ups(intent, repo_name),
        )

    async def _load_market_context(self, days: int) -> MarketBriefResponseDTO | None:
        try:
            return await self._market_brief_use_case.execute(
                days=days,
                breakout_limit=5,
                category_limit=5,
                topic_limit=8,
            )
        except AIInsightError as exc:
            logger.warning("ai_chat.market_context_unavailable", error=str(exc))
            return None

    async def _load_search_context(self, question: str, days: int) -> RepoSearchResponseDTO | None:
        try:
            return await self._search_use_case.execute(
                query=question,
                category=None,
                primary_language=None,
                min_stars=500,
                days=days,
                limit=5,
            )
        except (AISearchError, ValidationError) as exc:
            logger.warning("ai_chat.search_context_unavailable", error=str(exc))
            return None

    async def _load_repo_context(
        self,
        repo_name: str,
        days: int,
    ) -> RepoBriefResponseDTO | None:
        try:
            return await self._repo_brief_use_case.execute(repo_name=repo_name, days=days)
        except AIInsightError as exc:
            logger.warning("ai_chat.repo_context_unavailable", repo_name=repo_name, error=str(exc))
            return None

    async def _maybe_generate_answer(
        self,
        *,
        question: str,
        intent: Intent,
        evidence: list[AIChatEvidenceDTO],
    ) -> dict[str, Any] | None:
        if not self._llm_enabled or self._generation_service is None:
            return None
        try:
            payload = await self._generation_service.generate_json(
                prompt=_build_generation_prompt(question, intent, evidence),
                system_prompt=_SYSTEM_PROMPT.strip(),
                schema=_CHAT_SCHEMA,
            )
        except GenerationServiceError as exc:
            logger.warning("ai_chat.generation_unavailable", error=str(exc))
            return None
        if not _generated_answer_is_valid(payload):
            logger.warning("ai_chat.invalid_generation_payload")
            return None
        return {
            "answer": str(payload["answer"]).strip(),
            "follow_up_questions": [
                str(item).strip() for item in payload["follow_up_questions"][:4]
            ],
        }


def _extract_repo_name(question: str) -> str | None:
    match = _REPO_PATTERN.search(question)
    return match.group(0) if match else None


def _extract_repo_name_from_history(history: list[AIChatMessageDTO]) -> str | None:
    for message in reversed(history[-6:]):
        repo_name = _extract_repo_name(message.content)
        if repo_name is not None:
            return repo_name
    return None


def _detect_intent(question: str, repo_name: str | None) -> Intent:
    if repo_name is not None:
        return "repo"
    if _SEARCH_PATTERN.search(question):
        return "search"
    if _TOPIC_PATTERN.search(question) or _CATEGORY_PATTERN.search(question):
        return "market"
    return "mixed"


def _market_evidence(
    market: MarketBriefResponseDTO,
    question: str,
) -> list[AIChatEvidenceDTO]:
    evidence: list[AIChatEvidenceDTO] = []
    wants_categories = _CATEGORY_PATTERN.search(question) is not None
    wants_topics = _TOPIC_PATTERN.search(question) is not None
    include_breakouts = not wants_categories and not wants_topics
    include_categories = wants_categories or include_breakouts
    include_topics = wants_topics or include_breakouts

    if include_breakouts:
        for breakout in market.breakout_repos[:5]:
            evidence.append(
                AIChatEvidenceDTO(
                    label=breakout.repo.repo_full_name,
                    value=(
                        f"+{breakout.star_count_in_window} stars, "
                        f"{breakout.total_events_in_window} events, "
                        f"{breakout.unique_actors_in_window} actors"
                    ),
                    source="/ai/market-brief.breakout_repos",
                )
            )
    if include_categories:
        for category in market.category_movers[:4]:
            evidence.append(
                AIChatEvidenceDTO(
                    label=category.category,
                    value=(
                        f"{category.active_repo_count} active repos, "
                        f"+{category.total_stars_in_window} stars, "
                        f"leader {category.leader_repo_name}"
                    ),
                    source="/ai/market-brief.category_movers",
                )
            )
    if include_topics:
        for topic in market.topic_shifts[:5]:
            evidence.append(
                AIChatEvidenceDTO(
                    label=topic.topic,
                    value=f"+{topic.star_count_in_window} stars across {topic.repo_count} repos",
                    source="/ai/market-brief.topic_shifts",
                )
            )
    return evidence


def _search_evidence(search: RepoSearchResponseDTO) -> list[AIChatEvidenceDTO]:
    return [
        AIChatEvidenceDTO(
            label=result.repo.repo_full_name,
            value=(
                f"score {result.score:.2f}, +{result.star_count_in_window} stars, "
                f"{'; '.join(result.why_matched[:2])}"
            ),
            source="/ai/search.results",
        )
        for result in search.results[:5]
    ]


def _repo_evidence(repo_brief: RepoBriefResponseDTO) -> list[AIChatEvidenceDTO]:
    return [
        AIChatEvidenceDTO(
            label=repo_brief.repo.repo_full_name,
            value=(
                f"{repo_brief.trend_verdict}: +{repo_brief.star_count_in_window} stars, "
                f"{repo_brief.total_events_in_window} events, "
                f"{repo_brief.unique_actors_in_window} actors"
            ),
            source="/ai/repo-brief",
        ),
        AIChatEvidenceDTO(
            label="why_trending",
            value=repo_brief.why_trending,
            source="/ai/repo-brief",
        ),
    ]


def _build_template_answer(
    *,
    question: str,
    intent: Intent,
    evidence: list[AIChatEvidenceDTO],
    market: MarketBriefResponseDTO | None,
    search: RepoSearchResponseDTO | None,
    repo_brief: RepoBriefResponseDTO | None,
) -> str:
    if repo_brief is not None:
        return "\n".join(
            [
                f"{repo_brief.repo.repo_full_name} dang duoc xep la {repo_brief.trend_verdict}.",
                repo_brief.summary,
                (
                    f"Trong {repo_brief.window_days} ngay: "
                    f"+{repo_brief.star_count_in_window} stars, "
                    f"{repo_brief.total_events_in_window} events, "
                    f"{repo_brief.unique_actors_in_window} actors."
                ),
                f"Ly do chinh: {repo_brief.why_trending}",
            ]
        )

    if intent == "search" and search is not None and search.results:
        lines = ["Cac repo khop nhat voi cau hoi cua ban:"]
        lines.extend(
            (
                f"{index + 1}. {result.repo.repo_full_name}: score {result.score:.2f}, "
                f"+{result.star_count_in_window} stars trong cua so du lieu."
            )
            for index, result in enumerate(search.results[:5])
        )
        return "\n".join(lines)

    if market is not None and _TOPIC_PATTERN.search(question):
        lines = ["Cac topic dang co chuyen dong manh nhat:"]
        lines.extend(
            (
                f"{index + 1}. {item.topic}: +{item.star_count_in_window} stars "
                f"tren {item.repo_count} repos."
            )
            for index, item in enumerate(market.topic_shifts[:6])
        )
        return "\n".join(lines)

    if market is not None and _CATEGORY_PATTERN.search(question):
        lines = ["Cac category noi bat trong cua so hien tai:"]
        lines.extend(
            (
                f"{index + 1}. {item.category}: {item.active_repo_count} active repos, "
                f"+{item.total_stars_in_window} stars, leader {item.leader_repo_name}."
            )
            for index, item in enumerate(market.category_movers[:5])
        )
        return "\n".join(lines)

    lines = ["Mình đã truy vấn dữ liệu thật và thấy các tín hiệu chính sau:"]
    lines.extend(f"- {item.label}: {item.value} ({item.source})" for item in evidence[:8])
    return "\n".join(lines)


def _follow_ups(intent: Intent, repo_name: str | None) -> list[str]:
    if repo_name is not None:
        return [
            f"So sanh {repo_name} voi repo trending khac",
            f"Tim cac repo lien quan den {repo_name}",
            f"{repo_name} co watchout nao dang chu y?",
        ]
    if intent == "market":
        return [
            "Category nao dang tang nhanh nhat?",
            "Topic nao co rotation manh nhat?",
            "Repo nao nen theo doi tiep?",
        ]
    if intent == "search":
        return [
            "Loc ket qua chi Python",
            "Repo nao co momentum tot nhat trong nhom nay?",
            "Hay phan tich repo dau tien",
        ]
    return [
        "Repo nao dang tang sao nhanh nhat?",
        "Topic nao dang nong trong 7 ngay?",
        "Tim repo ve AI agents",
    ]


def _build_generation_prompt(
    question: str,
    intent: Intent,
    evidence: list[AIChatEvidenceDTO],
) -> str:
    evidence_lines = "\n".join(
        f"- {item.label}: {item.value} [source={item.source}]" for item in evidence[:16]
    )
    return f"""
Question: {question}
Detected intent: {intent}

Evidence:
{evidence_lines}

Return JSON matching the schema.
Answer in the same language style as the question when possible.
Mention concrete repositories, counts, and sources naturally.
""".strip()


def _generated_answer_is_valid(payload: dict[str, Any]) -> bool:
    answer = payload.get("answer")
    follow_ups = payload.get("follow_up_questions")
    return (
        isinstance(answer, str)
        and len(answer.strip()) > 0
        and isinstance(follow_ups, list)
        and all(isinstance(item, str) and item.strip() for item in follow_ups)
    )
