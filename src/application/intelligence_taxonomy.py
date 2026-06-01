"""Shared taxonomy and heuristic helpers for intelligence surfaces."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import re
from typing import cast

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

_FRAMEWORKS: dict[str, tuple[str, tuple[str, ...]]] = {
    "langchain": ("LangChain", ("langchain", "langgraph")),
    "crewai": ("CrewAI", ("crewai", "crew ai")),
    "autogen": ("AutoGen", ("autogen", "magentic")),
    "llamaindex": ("LlamaIndex", ("llamaindex", "gpt index")),
    "semantic-kernel": ("Semantic Kernel", ("semantic-kernel", "semantic kernel")),
    "browser-use": ("Browser Use", ("browser-use", "browser use")),
}

_ENTITY_PATTERNS: dict[str, tuple[str, ...]] = {
    "OpenAI": ("openai", "gpt", "o1", "o3", "realtime", "chatgpt"),
    "Anthropic": ("anthropic", "claude", "computer use"),
    "Google AI": ("google ai", "gemini", "vertex ai"),
    "Meta AI": ("meta", "llama"),
    "Microsoft": ("microsoft", "copilot", "autogen", "semantic kernel"),
}


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


def infer_categories(*parts: str) -> list[str]:
    """Infer product-facing categories from text fragments."""

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

    text = normalize_text(provider, *parts)
    entities = {provider}
    for entity, keywords in _ENTITY_PATTERNS.items():
        if any(keyword in text for keyword in keywords):
            entities.add(entity)

    title = parts[0] if parts else ""
    phrases = re.findall(r"\b[A-Z][A-Za-z0-9.+-]{2,}(?:\s+[A-Z0-9][A-Za-z0-9.+-]{1,})*", title)
    for phrase in phrases[:4]:
        entities.add(phrase.strip())

    return sorted(entities)


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
    """Return the stable framework/entity registry used by intelligence features."""

    return [
        FrameworkDefinition(framework_id=framework_id, framework_name=name, keywords=keywords)
        for framework_id, (name, keywords) in _FRAMEWORKS.items()
    ]


def infer_framework_matches(*parts: str) -> list[FrameworkDefinition]:
    """Return framework registry entries mentioned by text fragments."""

    text = normalize_text(*parts)
    matches = [
        item for item in framework_registry() if any(keyword in text for keyword in item.keywords)
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
