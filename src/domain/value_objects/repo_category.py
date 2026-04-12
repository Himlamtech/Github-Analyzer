"""RepoCategory value object — enumeration of AI repository categories.

Derived from topics[] using a deterministic priority-ordered rule set in
CategoryClassifier. The category is computed at sync time and stored in
repo_metadata for fast GROUP BY queries without runtime topic scanning.
"""

from __future__ import annotations

from enum import Enum


class RepoCategory(str, Enum):
    """AI repository category taxonomy.

    Priority order (highest wins when multiple topics match):
        1. LLM        — Large language models, transformers, fine-tuning
        2. Agent      — AI agents, multi-agent frameworks, RAG pipelines
        3. Diffusion  — Stable diffusion, image generation models
        4. Multimodal — Vision-language, audio, speech, multimodal models
        5. DataEng    — Vector DBs, embeddings, datasets, MLOps tooling
        6. Other      — AI/ML but uncategorized
    """

    LLM = "LLM"
    AGENT = "Agent"
    DIFFUSION = "Diffusion"
    MULTIMODAL = "Multimodal"
    DATA_ENG = "DataEng"
    OTHER = "Other"

    def __str__(self) -> str:
        return self.value
