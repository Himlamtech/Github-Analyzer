"""Unit tests for GitHub event admission filter."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from src.infrastructure.github.event_filter import PopularRepoFilter


@pytest.fixture
def filter_() -> PopularRepoFilter:
    return PopularRepoFilter()


def _make_event(
    *,
    actor_login: str = "dev",
    topics: list[str] | None = None,
    description: str = "",
    readme_text: str = "",
    issues: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    return {
        "id": "evt_001",
        "type": "PushEvent",
        "actor": {"id": 1, "login": actor_login},
        "repo": {"id": 123, "name": "owner/repo"},
        "payload": {},
        "created_at": datetime.now(tz=UTC).isoformat(),
        "public": True,
        "_full_repo": {
            "full_name": "owner/repo",
            "stargazers_count": 5,
            "topics": topics or [],
            "description": description,
        },
        "_repo_readme_text": readme_text,
        "_repo_issues": issues or [],
    }


def test_is_ai_relevant_topic_match_returns_true(filter_: PopularRepoFilter) -> None:
    assert filter_.is_ai_relevant(_make_event(topics=["llm", "transformer"])) is True


def test_is_ai_relevant_readme_signal_returns_true(filter_: PopularRepoFilter) -> None:
    event = _make_event(readme_text="A production-ready generative AI agent framework.")

    assert filter_.is_ai_relevant(event) is True


def test_is_ai_relevant_issue_title_signal_returns_true(filter_: PopularRepoFilter) -> None:
    event = _make_event(issues=[{"title": "Add multimodal embedding pipeline"}])

    assert filter_.is_ai_relevant(event) is True


def test_is_ai_relevant_non_ai_repo_returns_true(filter_: PopularRepoFilter) -> None:
    event = _make_event(
        topics=["database", "analytics"],
        description="A billing dashboard for ecommerce stores.",
    )

    assert filter_.is_ai_relevant(event) is True


def test_is_ai_relevant_bot_returns_true(filter_: PopularRepoFilter) -> None:
    assert filter_.is_ai_relevant(_make_event(actor_login="test[bot]", topics=["llm"])) is True


def test_is_ai_relevant_missing_full_repo_returns_true(filter_: PopularRepoFilter) -> None:
    event = _make_event()
    event["_full_repo"] = {}

    assert filter_.is_ai_relevant(event) is True


def test_is_ai_relevant_missing_repo_identity_returns_false(filter_: PopularRepoFilter) -> None:
    event = _make_event()
    event["repo"] = {"id": 0, "name": ""}

    assert filter_.is_ai_relevant(event) is False


def test_alias_is_same_class() -> None:
    from src.infrastructure.github.event_filter import AiEventFilter

    assert AiEventFilter is PopularRepoFilter


class TestPopularRepoFilterAiRelevance:
    """Additional tests for ai_relevant detection edge cases."""

    def test_is_ai_relevant_description_with_neural_network_returns_true(
        self, filter_: PopularRepoFilter
    ) -> None:
        """'neural network' in description must trigger AI relevance."""
        event = _make_event(description="A high-performance neural network inference library")
        assert filter_.is_ai_relevant(event) is True

    def test_is_ai_relevant_topic_diffusion_returns_true(self, filter_: PopularRepoFilter) -> None:
        """'diffusion' topic must trigger AI relevance."""
        event = _make_event(topics=["diffusion", "image-generation"])
        assert filter_.is_ai_relevant(event) is True

    def test_is_ai_relevant_readme_with_llm_returns_true(self, filter_: PopularRepoFilter) -> None:
        """README text containing 'LLM' must trigger AI relevance."""
        event = _make_event(readme_text="This tool benchmarks LLM inference speed.")
        assert filter_.is_ai_relevant(event) is True

    def test_is_ai_relevant_topic_rag_returns_true(self, filter_: PopularRepoFilter) -> None:
        """'rag' topic must trigger AI relevance."""
        event = _make_event(topics=["rag", "vector-db"])
        assert filter_.is_ai_relevant(event) is True

    def test_is_ai_relevant_multiple_non_ai_signals_still_false_when_identity_missing(
        self, filter_: PopularRepoFilter
    ) -> None:
        """Missing repo identity causes rejection regardless of AI signals."""
        event = _make_event(topics=["llm", "transformer"], description="A GPT wrapper")
        event["repo"] = {"id": 0, "name": ""}
        assert filter_.is_ai_relevant(event) is False
