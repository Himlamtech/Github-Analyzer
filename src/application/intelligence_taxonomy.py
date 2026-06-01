"""Shared registry and heuristic helpers for intelligence surfaces."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import re
from typing import cast

from src.domain.entities.intelligence_entity import IntelligenceEntity

_CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "Coding Agents & Automation": (
        "agent",
        "agents",
        "browser-use",
        "automation",
        "autonomous",
        "orchestration",
        "workflow",
        "operator",
        "assistant",
        "crew",
    ),
    "Reasoning Frameworks": (
        "reasoning",
        "o1",
        "o3",
        "deliberation",
        "chain-of-thought",
        "planning",
        "inference",
        "graph",
    ),
    "Multimodal Interfaces": (
        "multimodal",
        "vision",
        "image",
        "video",
        "voice",
        "audio",
        "speech",
        "realtime",
    ),
    "Data Infrastructure": (
        "rag",
        "retrieval",
        "embedding",
        "vector",
        "database",
        "search",
        "index",
        "knowledge",
    ),
    "Model Serving": (
        "serving",
        "inference-server",
        "deployment",
        "gpu",
        "runtime",
        "llm",
        "vllm",
        "ollama",
    ),
    "Developer Tooling": (
        "sdk",
        "framework",
        "cli",
        "typescript",
        "python",
        "tooling",
        "developer",
    ),
}

_REGISTRY: tuple[IntelligenceEntity, ...] = (
    IntelligenceEntity(
        entity_id="provider-openai",
        entity_type="provider",
        display_name="OpenAI",
        aliases=("openai", "chatgpt", "gpt", "o1", "o3", "realtime"),
        categories=("Reasoning Frameworks", "Model Serving"),
        framework_ids=("openai-agents",),
    ),
    IntelligenceEntity(
        entity_id="provider-anthropic",
        entity_type="provider",
        display_name="Anthropic",
        aliases=("anthropic", "claude", "computer use"),
        categories=("Coding Agents & Automation", "Reasoning Frameworks"),
        framework_ids=("anthropic-agents",),
    ),
    IntelligenceEntity(
        entity_id="provider-google-ai",
        entity_type="provider",
        display_name="Google AI",
        aliases=("google ai", "gemini", "vertex ai"),
        categories=("Multimodal Interfaces", "Model Serving"),
    ),
    IntelligenceEntity(
        entity_id="category-agentic-frameworks",
        entity_type="category",
        display_name="Agentic Frameworks",
        aliases=("agentic-frameworks", "agentic frameworks"),
        categories=("Coding Agents & Automation",),
    ),
    IntelligenceEntity(
        entity_id="framework-langchain",
        entity_type="framework",
        display_name="LangChain",
        aliases=("langchain", "langgraph"),
        categories=("Developer Tooling", "Coding Agents & Automation"),
        repo_full_names=("langchain-ai/langchain", "langchain-ai/langgraph"),
        framework_ids=("langchain",),
    ),
    IntelligenceEntity(
        entity_id="framework-crewai",
        entity_type="framework",
        display_name="CrewAI",
        aliases=("crewai", "crew ai"),
        categories=("Coding Agents & Automation",),
        repo_full_names=("crewAIInc/crewAI",),
        framework_ids=("crewai",),
    ),
    IntelligenceEntity(
        entity_id="framework-autogen",
        entity_type="framework",
        display_name="AutoGen",
        aliases=("autogen", "magentic"),
        categories=("Coding Agents & Automation", "Reasoning Frameworks"),
        repo_full_names=("microsoft/autogen",),
        framework_ids=("autogen",),
    ),
    IntelligenceEntity(
        entity_id="framework-llamaindex",
        entity_type="framework",
        display_name="LlamaIndex",
        aliases=("llamaindex", "gpt index"),
        categories=("Data Infrastructure", "Developer Tooling"),
        repo_full_names=("run-llama/llama_index",),
        framework_ids=("llamaindex",),
    ),
    IntelligenceEntity(
        entity_id="framework-semantic-kernel",
        entity_type="framework",
        display_name="Semantic Kernel",
        aliases=("semantic-kernel", "semantic kernel"),
        categories=("Developer Tooling",),
        repo_full_names=("microsoft/semantic-kernel",),
        framework_ids=("semantic-kernel",),
    ),
    IntelligenceEntity(
        entity_id="framework-browser-use",
        entity_type="framework",
        display_name="Browser Use",
        aliases=("browser-use", "browser use", "browser agent", "browser agents"),
        categories=("Coding Agents & Automation",),
        repo_full_names=("browser-use/browser-use",),
        framework_ids=("browser-use",),
    ),
)


@dataclass(frozen=True, slots=True)
class FrameworkDefinition:
    """Stable framework registry definition."""

    framework_id: str
    framework_name: str
    keywords: tuple[str, ...]


def normalize_text(*parts: str) -> str:
    """Normalize text fragments for keyword matching."""

    combined = " ".join(part.strip().lower() for part in parts if part.strip())
    return re.sub(r"\s+", " ", combined)


def intelligence_registry() -> tuple[IntelligenceEntity, ...]:
    """Return the structured intelligence registry used across use cases."""

    return _REGISTRY


def infer_registry_matches(*parts: str) -> list[IntelligenceEntity]:
    """Return registry entities matched by normalized content text."""

    text = normalize_text(*parts)
    matches = [
        entity
        for entity in intelligence_registry()
        if any(alias in text for alias in entity.aliases) or entity.display_name.lower() in text
    ]
    return sorted(matches, key=lambda item: (item.entity_type, item.display_name))


def infer_categories(*parts: str) -> list[str]:
    """Infer product-facing categories from text fragments."""

    registry_matches = infer_registry_matches(*parts)
    registry_categories = list(
        dict.fromkeys(
            category for entity in registry_matches for category in entity.categories if category
        )
    )
    if registry_categories:
        return registry_categories[:2]

    text = normalize_text(*parts)
    scores: list[tuple[str, int]] = []
    for category, keywords in _CATEGORY_KEYWORDS.items():
        score = sum(1 for keyword in keywords if keyword in text)
        if score:
            scores.append((category, score))

    if not scores:
        return ["Developer Tooling"]

    ranked = sorted(scores, key=lambda item: (-item[1], item[0]))
    return [category for category, _ in ranked[:2]]


def infer_entities(provider: str, *parts: str) -> list[str]:
    """Infer named entities from provider and content text."""

    registry_matches = infer_registry_matches(provider, *parts)
    entities = {provider}
    entities.update(entity.display_name for entity in registry_matches)

    title = parts[0] if parts else ""
    phrases = re.findall(r"\b[A-Z][A-Za-z0-9.+-]{2,}(?:\s+[A-Z0-9][A-Za-z0-9.+-]{1,})*", title)
    for phrase in phrases[:4]:
        entities.add(phrase.strip())

    return sorted(entities)


def infer_linked_repos(provider: str, *parts: str) -> list[str]:
    """Infer linked repositories from the structured registry."""

    matches = infer_registry_matches(provider, *parts)
    repos = list(
        dict.fromkeys(repo for entity in matches for repo in entity.repo_full_names if repo)
    )
    return repos


def infer_linked_frameworks(provider: str, *parts: str) -> list[str]:
    """Infer linked framework IDs from the structured registry."""

    matches = infer_registry_matches(provider, *parts)
    frameworks = list(
        dict.fromkeys(
            framework_id
            for entity in matches
            for framework_id in entity.framework_ids
            if framework_id
        )
    )
    return frameworks


def infer_event_type(*parts: str) -> str:
    """Infer a coarse event type from text fragments."""

    text = normalize_text(*parts)
    if any(keyword in text for keyword in ("launch", "release", "introducing", "announce")):
        return "launch"
    if any(keyword in text for keyword in ("research", "paper", "study", "benchmark")):
        return "research"
    if any(keyword in text for keyword in ("api", "sdk", "tool", "framework")):
        return "product"
    return "news"


def compute_quality_score(title: str, summary: str) -> float:
    """Score content quality for ingestion integrity decisions."""

    score = 45.0
    if len(title.strip()) >= 18:
        score += 20.0
    if len(summary.strip()) >= 40:
        score += 20.0
    if "http" not in summary.lower():
        score += 5.0
    if any(char.isdigit() for char in title):
        score += 5.0
    return max(0.0, min(score, 100.0))


def should_quarantine(
    *, title: str, url: str, quality_score: float, duplicate: bool
) -> str | None:
    """Return a quarantine reason when an item should not be served live."""

    if not title.strip() or not url.strip():
        return "missing_required_fields"
    if duplicate:
        return "duplicate_content"
    if quality_score < 55.0:
        return "low_confidence_content"
    return None


def framework_registry() -> list[FrameworkDefinition]:
    """Return stable framework registry definitions."""

    return [
        FrameworkDefinition(
            framework_id=entity.framework_ids[0],
            framework_name=entity.display_name,
            keywords=tuple(dict.fromkeys((*entity.aliases, *entity.repo_full_names))),
        )
        for entity in intelligence_registry()
        if entity.entity_type == "framework" and entity.framework_ids
    ]


def infer_framework_matches(*parts: str) -> list[FrameworkDefinition]:
    """Return framework registry entries mentioned by text fragments."""

    text = normalize_text(*parts)
    matches = [
        item
        for item in framework_registry()
        if any(keyword.lower() in text for keyword in item.keywords)
    ]
    return matches


def summarize_repo_topics(rows: list[dict[str, object]], limit: int = 3) -> list[str]:
    """Return the most common topics across repository rows."""

    counts: Counter[str] = Counter()
    for row in rows:
        for topic in cast("list[str]", row.get("topics") or []):
            counts[str(topic)] += 1
    return [topic for topic, _ in counts.most_common(limit)]


def titleize_token(value: str) -> str:
    """Turn a topic token into readable UI text."""

    return " ".join(part.capitalize() for part in value.replace("_", "-").split("-")) or "Other"
