"""Unit tests for CategoryClassifier domain service.

Test naming: test_classify_<scenario>_<expected_result>
"""

from __future__ import annotations

import pytest

from src.domain.services.category_classifier import CategoryClassifier
from src.domain.value_objects.repo_category import RepoCategory


@pytest.fixture
def classifier() -> CategoryClassifier:
    return CategoryClassifier()


# ── Topic-based classification ────────────────────────────────────────────────


class TestTopicClassification:
    def test_classify_llm_topic_returns_llm(self, classifier: CategoryClassifier) -> None:
        # Arrange
        topics = ["llm", "transformer", "python"]
        # Act
        result = classifier.classify(topics=topics, description="")
        # Assert
        assert result == RepoCategory.LLM

    def test_classify_agent_topic_returns_agent(self, classifier: CategoryClassifier) -> None:
        topics = ["agent", "langchain"]
        result = classifier.classify(topics=topics, description="")
        assert result == RepoCategory.AGENT

    def test_classify_diffusion_topic_returns_diffusion(
        self, classifier: CategoryClassifier
    ) -> None:
        topics = ["diffusion", "stable-diffusion"]
        result = classifier.classify(topics=topics, description="")
        assert result == RepoCategory.DIFFUSION

    def test_classify_multimodal_topic_returns_multimodal(
        self, classifier: CategoryClassifier
    ) -> None:
        topics = ["multimodal", "vision"]
        result = classifier.classify(topics=topics, description="")
        assert result == RepoCategory.MULTIMODAL

    def test_classify_dataeng_topic_returns_dataeng(self, classifier: CategoryClassifier) -> None:
        topics = ["vector-db", "embedding"]
        result = classifier.classify(topics=topics, description="")
        assert result == RepoCategory.DATA_ENG

    def test_classify_model_name_in_topic_returns_llm(
        self, classifier: CategoryClassifier
    ) -> None:
        topics = ["llama", "quantization"]
        result = classifier.classify(topics=topics, description="")
        assert result == RepoCategory.LLM

    def test_classify_rag_topic_returns_agent(self, classifier: CategoryClassifier) -> None:
        topics = ["rag"]
        result = classifier.classify(topics=topics, description="")
        assert result == RepoCategory.AGENT


# ── Priority ordering ─────────────────────────────────────────────────────────


class TestPriorityOrdering:
    def test_classify_llm_beats_agent_when_both_match(
        self, classifier: CategoryClassifier
    ) -> None:
        """LLM has higher priority than Agent."""
        topics = ["llm", "agent"]  # both match; LLM wins
        result = classifier.classify(topics=topics, description="")
        assert result == RepoCategory.LLM

    def test_classify_llm_beats_dataeng_when_both_match(
        self, classifier: CategoryClassifier
    ) -> None:
        topics = ["transformer", "embedding"]
        result = classifier.classify(topics=topics, description="")
        assert result == RepoCategory.LLM

    def test_classify_agent_beats_diffusion_when_both_match(
        self, classifier: CategoryClassifier
    ) -> None:
        topics = ["agent", "diffusion"]
        result = classifier.classify(topics=topics, description="")
        assert result == RepoCategory.AGENT


# ── Description keyword fallback ──────────────────────────────────────────────


class TestDescriptionFallback:
    def test_classify_llm_keyword_in_description_returns_llm(
        self, classifier: CategoryClassifier
    ) -> None:
        result = classifier.classify(
            topics=[],
            description="A large language model fine-tuning toolkit",
        )
        assert result == RepoCategory.LLM

    def test_classify_agent_keyword_in_description_returns_agent(
        self, classifier: CategoryClassifier
    ) -> None:
        result = classifier.classify(
            topics=[],
            description="Build autonomous agent pipelines with RAG pipeline support",
        )
        assert result == RepoCategory.AGENT

    def test_classify_diffusion_keyword_in_description_returns_diffusion(
        self, classifier: CategoryClassifier
    ) -> None:
        result = classifier.classify(
            topics=[],
            description="Fast stable diffusion inference on consumer hardware",
        )
        assert result == RepoCategory.DIFFUSION


# ── Fallback to OTHER ─────────────────────────────────────────────────────────


class TestOtherFallback:
    def test_classify_empty_topics_empty_description_returns_other(
        self, classifier: CategoryClassifier
    ) -> None:
        result = classifier.classify(topics=[], description="")
        assert result == RepoCategory.OTHER

    def test_classify_unrelated_topics_returns_other(self, classifier: CategoryClassifier) -> None:
        result = classifier.classify(
            topics=["web-scraping", "javascript", "nodejs"],
            description="A web scraping utility",
        )
        assert result == RepoCategory.OTHER

    def test_classify_topics_normalised_to_lowercase(self, classifier: CategoryClassifier) -> None:
        """Topic matching must be case-insensitive."""
        result = classifier.classify(topics=["LLM", "Transformer"], description="")
        assert result == RepoCategory.LLM


class TestCategoryClassifierEdgeCases:
    """Edge case tests for CategoryClassifier."""

    def test_classify_none_like_empty_description_returns_other(
        self, classifier: CategoryClassifier
    ) -> None:
        """Whitespace-only description must be treated as empty."""
        result = classifier.classify(topics=[], description="   ")
        assert result == RepoCategory.OTHER

    def test_classify_topics_with_empty_strings_returns_other(
        self, classifier: CategoryClassifier
    ) -> None:
        """Topics list containing only empty strings must fall back to OTHER."""
        result = classifier.classify(topics=["", "  "], description="")
        assert result == RepoCategory.OTHER

    def test_classify_description_keyword_deepseek_returns_llm(
        self, classifier: CategoryClassifier
    ) -> None:
        """'deepseek' keyword in description must resolve to LLM category."""
        result = classifier.classify(
            topics=[],
            description="DeepSeek-V3 inference server",
        )
        assert result == RepoCategory.LLM

    def test_classify_multimodal_topic_beats_dataeng(self, classifier: CategoryClassifier) -> None:
        """Multimodal has higher priority than DataEng."""
        result = classifier.classify(
            topics=["multimodal", "vector-db"],
            description="",
        )
        assert result == RepoCategory.MULTIMODAL

    def test_classify_dataeng_beats_other(self, classifier: CategoryClassifier) -> None:
        """DataEng must win over OTHER when a DataEng topic is present."""
        result = classifier.classify(topics=["vector-db"], description="")
        assert result == RepoCategory.DATA_ENG

    def test_classify_single_llm_topic_returns_llm(self, classifier: CategoryClassifier) -> None:
        """A single matching LLM topic is sufficient to classify as LLM."""
        result = classifier.classify(topics=["llm"], description="")
        assert result == RepoCategory.LLM
