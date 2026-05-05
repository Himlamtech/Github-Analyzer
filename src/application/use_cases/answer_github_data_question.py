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

_SYSTEM_PROMPT = """
You are a grounded GitHub AI data analyst.
Answer only from the provided evidence.
Do not invent repositories, star counts, categories, topics, or causes.
Keep the answer concise, useful, and direct.
"""

_INTENT_SYSTEM_PROMPT = """
You are an intent classifier for a GitHub data analytics chatbot.
Classify the user's question into exactly one of three intents:

- instant: The question can be answered directly from general knowledge without querying any database. Examples: explain what a topic is, define a term, give advice on open source strategy, general questions about GitHub or software.
- search: The user wants to discover or find repositories matching a description, technology, or use case. Examples: "find repos about X", "search for Y", "goi y repo ve Z", "repositories related to".
- knowledge: The user wants statistics, trends, rankings, topic shifts, category movements, repo analytics, or any data that must come from the live database. Examples: "repo nao tang nhanh", "topic nao hot", "phan tich owner/repo", "category nao dang dich chuyen", star counts, breakout repos.

Return only valid JSON: {"intent": "instant"|"search"|"knowledge"}
""".strip()

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

_INTENT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "intent": {"type": "string", "enum": ["instant", "search", "knowledge"]},
    },
    "required": ["intent"],
}

_INSTANT_SCHEMA: dict[str, Any] = {
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

AgentIntent = Literal["instant", "search", "knowledge"]
Intent = Literal["instant", "search", "knowledge", "market", "repo", "mixed"]


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

        agent_intent = await self._classify_intent(normalized_question)
        logger.info("ai_chat.intent_classified", intent=agent_intent, question=normalized_question[:80])

        if agent_intent == "instant":
            return await self._handle_instant(normalized_question, history)

        if agent_intent == "search":
            return await self._handle_search(normalized_question, days)

        # knowledge intent — fetch data from DB based on query details
        return await self._handle_knowledge(normalized_question, days, history)

    async def _classify_intent(self, question: str) -> AgentIntent:
        """Use LLM to classify question intent; fall back to heuristic."""
        if self._llm_enabled and self._generation_service is not None:
            try:
                result = await self._generation_service.generate_json(
                    prompt=f"Question: {question}",
                    system_prompt=_INTENT_SYSTEM_PROMPT,
                    schema=_INTENT_SCHEMA,
                )
                intent_value = result.get("intent", "")
                if intent_value in ("instant", "search", "knowledge"):
                    return intent_value  # type: ignore[return-value]
            except GenerationServiceError as exc:
                logger.warning("ai_chat.intent_classification_failed", error=str(exc))

        return _heuristic_intent(question)

    async def _handle_instant(
        self,
        question: str,
        history: list[AIChatMessageDTO] | None,
    ) -> AIChatResponseDTO:
        """Answer directly using LLM general knowledge, no DB queries."""
        if self._llm_enabled and self._generation_service is not None:
            try:
                history_text = _format_history(history)
                prompt = (
                    f"{history_text}\nQuestion: {question}"
                    if history_text
                    else f"Question: {question}"
                )
                result = await self._generation_service.generate_json(
                    prompt=prompt,
                    system_prompt=(
                        "You are a helpful GitHub and open source expert. "
                        "Answer the user's question clearly and concisely. "
                        "Also suggest 2-4 follow-up questions."
                    ),
                    schema=_INSTANT_SCHEMA,
                )
                if _generated_answer_is_valid(result):
                    return AIChatResponseDTO(
                        answer=str(result["answer"]).strip(),
                        mode="model",
                        intent="instant",
                        tools_used=[],
                        evidence=[],
                        follow_up_questions=[
                            str(q).strip() for q in result["follow_up_questions"][:4]
                        ],
                    )
            except GenerationServiceError as exc:
                logger.warning("ai_chat.instant_generation_failed", error=str(exc))

        return AIChatResponseDTO(
            answer="Xin loi, minh chua the tra loi cau hoi nay ngay luc nay.",
            mode="template",
            intent="instant",
            tools_used=[],
            evidence=[],
            follow_up_questions=_default_follow_ups(),
        )

    async def _handle_search(self, question: str, days: int) -> AIChatResponseDTO:
        """Search for repositories matching the query."""
        search = await self._load_search_context(question, days)
        if search is None or not search.results:
            raise AIInsightError("No search results found for this query.")

        evidence = _search_evidence(search)
        tools_used = ["search"]

        generated = await self._maybe_generate_answer(
            question=question,
            intent="search",
            evidence=evidence,
        )
        if generated is not None:
            return AIChatResponseDTO(
                answer=generated["answer"],
                mode="model",
                intent="search",
                tools_used=tools_used,
                evidence=evidence[:12],
                follow_up_questions=generated["follow_up_questions"],
            )

        lines = ["Cac repo khop nhat voi cau hoi cua ban:"]
        lines.extend(
            f"{i + 1}. {r.repo.repo_full_name}: score {r.score:.2f}, "
            f"+{r.star_count_in_window} stars."
            for i, r in enumerate(search.results[:5])
        )
        return AIChatResponseDTO(
            answer="\n".join(lines),
            mode="template",
            intent="search",
            tools_used=tools_used,
            evidence=evidence[:12],
            follow_up_questions=_search_follow_ups(),
        )

    async def _handle_knowledge(
        self,
        question: str,
        days: int,
        history: list[AIChatMessageDTO] | None,
    ) -> AIChatResponseDTO:
        """Query DB for market data, repo briefs, or search results based on question details."""
        repo_name = _extract_repo_name(question)
        if repo_name is None and history:
            repo_name = _extract_repo_name_from_history(history)

        tools_used: list[str] = []
        evidence: list[AIChatEvidenceDTO] = []

        # Always load market context for knowledge queries
        market = await self._load_market_context(days)
        if market is not None:
            tools_used.append("market-brief")
            evidence.extend(_market_evidence(market, question))

        # Load search context as additional signal
        search = await self._load_search_context(question, days)
        if search is not None:
            tools_used.append("search")
            evidence.extend(_search_evidence(search))

        # Load specific repo brief if mentioned
        repo_brief: RepoBriefResponseDTO | None = None
        if repo_name is not None:
            repo_brief = await self._load_repo_context(repo_name, days)
            if repo_brief is not None:
                tools_used.append("repo-brief")
                evidence.extend(_repo_evidence(repo_brief))

        if not evidence:
            raise AIInsightError("No GitHub trend data was available for this query.")

        # Determine fine-grained intent for template fallback
        fine_intent: Intent = "repo" if repo_name else "knowledge"

        generated = await self._maybe_generate_answer(
            question=question,
            intent=fine_intent,
            evidence=evidence,
        )
        if generated is not None:
            return AIChatResponseDTO(
                answer=generated["answer"],
                mode="model",
                intent=fine_intent,
                tools_used=tools_used,
                evidence=evidence[:12],
                follow_up_questions=generated["follow_up_questions"],
            )

        return AIChatResponseDTO(
            answer=_build_template_answer(
                question=question,
                intent=fine_intent,
                evidence=evidence,
                market=market,
                search=search,
                repo_brief=repo_brief,
            ),
            mode="template",
            intent=fine_intent,
            tools_used=tools_used,
            evidence=evidence[:12],
            follow_up_questions=_knowledge_follow_ups(repo_name),
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


def _heuristic_intent(question: str) -> AgentIntent:
    """Regex fallback when LLM classifier is unavailable."""
    if _REPO_PATTERN.search(question):
        return "knowledge"
    search_pat = re.compile(
        r"\b(search|find|tim|tim kiem|goi y|repo ve|repositories about)\b", re.I
    )
    if search_pat.search(question):
        return "search"
    knowledge_pat = re.compile(
        r"\b(trend|trending|tang|hot|breakout|sao|star|category|topic|phan tich|"
        r"chu de|danh muc|nhom|rotation|dich chuyen|nhanh nhat|noi bat)\b",
        re.I,
    )
    if knowledge_pat.search(question):
        return "knowledge"
    return "instant"


def _extract_repo_name(question: str) -> str | None:
    match = _REPO_PATTERN.search(question)
    return match.group(0) if match else None


def _extract_repo_name_from_history(history: list[AIChatMessageDTO]) -> str | None:
    for message in reversed(history[-6:]):
        repo_name = _extract_repo_name(message.content)
        if repo_name is not None:
            return repo_name
    return None


def _format_history(history: list[AIChatMessageDTO] | None) -> str:
    if not history:
        return ""
    lines = []
    for msg in history[-6:]:
        prefix = "User" if msg.role == "user" else "Assistant"
        lines.append(f"{prefix}: {msg.content}")
    return "\n".join(lines)


def _market_evidence(
    market: MarketBriefResponseDTO,
    question: str,
) -> list[AIChatEvidenceDTO]:
    _TOPIC_PATTERN = re.compile(r"\b(topic|topics|tag|tags|chu de|stack|cong nghe)\b", re.I)
    _CATEGORY_PATTERN = re.compile(r"\b(category|categories|danh muc|nhom|phan khuc)\b", re.I)

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
    _TOPIC_PATTERN = re.compile(r"\b(topic|topics|tag|tags|chu de|stack|cong nghe)\b", re.I)
    _CATEGORY_PATTERN = re.compile(r"\b(category|categories|danh muc|nhom|phan khuc)\b", re.I)

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

    lines = ["Minh da truy van du lieu that va thay cac tin hieu chinh sau:"]
    lines.extend(f"- {item.label}: {item.value} ({item.source})" for item in evidence[:8])
    return "\n".join(lines)


def _default_follow_ups() -> list[str]:
    return [
        "Repo nao dang tang sao nhanh nhat?",
        "Topic nao dang nong trong 7 ngay?",
        "Tim repo ve AI agents",
    ]


def _search_follow_ups() -> list[str]:
    return [
        "Loc ket qua chi Python",
        "Repo nao co momentum tot nhat trong nhom nay?",
        "Hay phan tich repo dau tien",
    ]


def _knowledge_follow_ups(repo_name: str | None) -> list[str]:
    if repo_name is not None:
        return [
            f"So sanh {repo_name} voi repo trending khac",
            f"Tim cac repo lien quan den {repo_name}",
            f"{repo_name} co watchout nao dang chu y?",
        ]
    return [
        "Category nao dang tang nhanh nhat?",
        "Topic nao co rotation manh nhat?",
        "Repo nao nen theo doi tiep?",
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
