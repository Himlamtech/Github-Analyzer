"""DTOs for grounded GitHub data chat responses."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class AIChatMessageDTO(BaseModel):
    """One chat message sent from the frontend."""

    model_config = ConfigDict(frozen=True)

    role: Literal["user", "assistant"]
    content: str = Field(..., min_length=1, max_length=4_000)


class AIChatRequestDTO(BaseModel):
    """Request payload for the GitHub data chat agent."""

    model_config = ConfigDict(frozen=True)

    question: str = Field(..., min_length=2, max_length=500)
    days: int = Field(default=30, ge=1, le=365)
    history: list[AIChatMessageDTO] = Field(default_factory=list, max_length=12)


class AIChatEvidenceDTO(BaseModel):
    """One grounded fact used by the chat agent."""

    model_config = ConfigDict(frozen=True)

    label: str
    value: str
    source: str


class AIChatResponseDTO(BaseModel):
    """Grounded answer returned by the GitHub data chat agent."""

    model_config = ConfigDict(frozen=True)

    answer: str
    mode: Literal["template", "model"]
    intent: Literal["market", "repo", "search", "mixed"]
    tools_used: list[str]
    evidence: list[AIChatEvidenceDTO]
    follow_up_questions: list[str]
