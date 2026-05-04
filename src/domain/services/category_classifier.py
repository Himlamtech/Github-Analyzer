"""CategoryClassifier domain service — maps topics[] to RepoCategory.

Stateless pure function.  Priority-ordered: first rule set to match wins.
Topic lists are normalised to lowercase before comparison.
Description keyword scan is used as a fallback when no topics match.
"""

from __future__ import annotations

from src.domain.value_objects.repo_category import RepoCategory

# ── Priority-ordered topic rule sets ─────────────────────────────────────────
# Each entry: (category, frozenset_of_matching_topics).
# Evaluation stops at the first match.

_CATEGORY_RULES: tuple[tuple[RepoCategory, frozenset[str]], ...] = (
    (
        RepoCategory.LLM,
        frozenset(
            {
                "llm",
                "transformer",
                "large-language-model",
                "fine-tuning",
                "pretrained-models",
                "language-model",
                "gpt",
                "bert",
                "llama",
                "mistral",
                "gemma",
                "phi",
                "falcon",
                "bloom",
                "qwen",
                "deepseek",
                "mixtral",
                "claude",
                "palm",
            }
        ),
    ),
    (
        RepoCategory.AGENT,
        frozenset(
            {
                "agent",
                "rag",
                "langchain",
                "multi-agent",
                "ai-agents",
                "autonomous-agent",
                "agentic",
                "tool-use",
                "function-calling",
                "retrieval-augmented-generation",
                "llamaindex",
                "autogpt",
                "crewai",
            }
        ),
    ),
    (
        RepoCategory.DIFFUSION,
        frozenset(
            {
                "diffusion",
                "stable-diffusion",
                "image-generation",
                "text-to-image",
                "latent-diffusion",
                "stable-diffusion-webui",
                "img2img",
                "dalle",
                "midjourney",
            }
        ),
    ),
    (
        RepoCategory.MULTIMODAL,
        frozenset(
            {
                "multimodal",
                "vision-language",
                "vlm",
                "audio",
                "speech",
                "speech-recognition",
                "text-to-speech",
                "vision",
                "ocr",
                "image-captioning",
                "video-understanding",
            }
        ),
    ),
    (
        RepoCategory.DATA_ENG,
        frozenset(
            {
                "vector-db",
                "embedding",
                "embeddings",
                "vector-search",
                "similarity-search",
                "huggingface",
                "model-hub",
                "dataset",
                "annotation",
                "mlops",
                "feature-store",
                "data-pipeline",
                "knowledge-graph",
            }
        ),
    ),
)

# ── Description keyword fallback ─────────────────────────────────────────────
# Applied only when topic matching yields no result.
# Each entry: (category, tuple_of_lowercase_substring_keywords).

_DESCRIPTION_KEYWORD_MAP: tuple[tuple[RepoCategory, tuple[str, ...]], ...] = (
    (
        RepoCategory.LLM,
        ("large language model", "llm", "language model", "deepseek"),
    ),
    (RepoCategory.AGENT, ("agent", "retrieval augmented", "rag pipeline", "agentic")),
    (RepoCategory.DIFFUSION, ("stable diffusion", "image generation", "diffusion model")),
    (RepoCategory.MULTIMODAL, ("multimodal", "vision language", "speech recognition")),
    (RepoCategory.DATA_ENG, ("vector database", "embedding", "vector store", "knowledge graph")),
)


class CategoryClassifier:
    """Classifies a repository into a RepoCategory.

    Evaluation order:
    1. Topic exact-match against priority-ordered rule sets (fastest).
    2. Description keyword substring scan (lowercase).
    3. Falls back to ``RepoCategory.OTHER``.

    This is a Domain Service: stateless, no dependencies, pure logic.
    """

    def classify(
        self,
        topics: list[str],
        description: str,
    ) -> RepoCategory:
        """Return the highest-priority matching category.

        Args:
            topics:      List of GitHub topic strings for the repository.
            description: Repository description text (may be empty).

        Returns:
            The matched ``RepoCategory``, or ``OTHER`` if no rule matches.
        """
        normalised_topics = frozenset(t.lower().strip() for t in topics if t)

        for category, rule_topics in _CATEGORY_RULES:
            if normalised_topics & rule_topics:
                return category

        lower_desc = description.lower()
        for category, keywords in _DESCRIPTION_KEYWORD_MAP:
            if any(kw in lower_desc for kw in keywords):
                return category

        return RepoCategory.OTHER
