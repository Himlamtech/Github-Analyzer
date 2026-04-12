"""GitHub event admission filter.

The previous implementation acted as an AI-only gate and discarded repositories
that were not classified as AI/ML-related. That behavior caused the ingest
pipeline to miss high-signal repositories such as ``torvalds/linux`` and
``facebook/react`` entirely.

This filter now accepts every structurally valid GitHub event so the pipeline
retains the full repository stream. AI/ML classification is still computed as a
debug signal, but it is no longer a hard drop condition.
"""

from __future__ import annotations

import structlog

from src.domain.services.category_classifier import CategoryClassifier
from src.domain.value_objects.repo_category import RepoCategory

logger = structlog.get_logger(__name__)

_AI_SIGNAL_KEYWORDS: frozenset[str] = frozenset(
    {
        "ai",
        "ml",
        "machine learning",
        "deep learning",
        "neural network",
        "generative ai",
        "llm",
        "large language model",
        "language model",
        "agent",
        "rag",
        "embedding",
        "vector database",
        "multimodal",
        "diffusion",
        "stable diffusion",
        "computer vision",
        "speech recognition",
    }
)


class PopularRepoFilter:
    """Accept structurally valid GitHub events for downstream ingestion."""

    def __init__(self, classifier: CategoryClassifier | None = None) -> None:
        self._classifier = classifier or CategoryClassifier()

    @staticmethod
    def _coerce_int(value: object) -> int:
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        if isinstance(value, str):
            try:
                return int(value)
            except ValueError:
                return 0
        return 0

    @staticmethod
    def _as_dict(value: object) -> dict[str, object]:
        return value if isinstance(value, dict) else {}

    def _extract_topics(self, full_repo: dict[str, object]) -> list[str]:
        topics_raw = full_repo.get("topics")
        if not isinstance(topics_raw, list):
            return []
        return [str(topic).strip() for topic in topics_raw if str(topic).strip()]

    def _build_description_text(
        self,
        event: dict[str, object],
        full_repo: dict[str, object],
    ) -> str:
        parts: list[str] = []

        description = str(full_repo.get("description") or "").strip()
        if description:
            parts.append(description)

        readme_text = str(event.get("_repo_readme_text") or "").strip()
        if readme_text:
            parts.append(readme_text[:2_000])

        issues = event.get("_repo_issues") or []
        if isinstance(issues, list):
            issue_titles = []
            for issue in issues:
                if not isinstance(issue, dict):
                    continue
                issue_title = str(issue.get("title") or "").strip()
                if issue_title:
                    issue_titles.append(issue_title)
            if issue_titles:
                parts.append(" ".join(issue_titles[:10]))

        return " ".join(parts)

    def _has_keyword_signal(self, text: str) -> bool:
        lowered = text.lower()
        return any(keyword in lowered for keyword in _AI_SIGNAL_KEYWORDS)

    def is_ai_relevant(self, event: dict[str, object]) -> bool:
        """Return True when the event is valid enough to retain.

        The method name is preserved for backward compatibility with the
        existing use case wiring and tests.
        """
        actor = self._as_dict(event.get("actor"))
        repo = self._as_dict(event.get("repo"))
        actor_login = str(actor.get("login") or "").strip()
        repo_name = str(repo.get("name") or "").strip()
        repo_id = self._coerce_int(repo.get("id"))

        if not actor_login or not repo_name or repo_id <= 0:
            logger.debug(
                "popular_repo_filter.discarded_invalid_event",
                event_id=str(event.get("id") or ""),
                actor_login=actor_login,
                repo_name=repo_name,
                repo_id=repo_id,
            )
            return False

        full_repo = self._as_dict(event.get("_full_repo"))

        topics = self._extract_topics(full_repo)
        description_text = self._build_description_text(event, full_repo)
        category = self._classifier.classify(topics=topics, description=description_text)
        has_ai_signal = category is not RepoCategory.OTHER or self._has_keyword_signal(
            description_text
        )

        logger.debug(
            "popular_repo_filter.accepted",
            repo=repo_name,
            ai_signal=has_ai_signal,
            category=str(category),
            topics=topics[:5],
        )
        return True


AiEventFilter = PopularRepoFilter
