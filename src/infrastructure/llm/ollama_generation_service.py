"""Ollama-backed structured generation service."""

from __future__ import annotations

import json
from typing import Any

import httpx
import structlog

from src.domain.exceptions import GenerationServiceError

logger = structlog.get_logger(__name__)


class OllamaGenerationService:
    """Generate structured JSON from a prompt using Ollama."""

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        timeout_seconds: float,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout_seconds = timeout_seconds

    async def generate_json(
        self,
        *,
        prompt: str,
        system_prompt: str,
        schema: dict[str, Any],
    ) -> dict[str, Any]:
        """Return a JSON object produced according to the provided schema."""
        url = f"{self._base_url}/api/generate"
        payload = {
            "model": self._model,
            "prompt": prompt,
            "system": system_prompt,
            "format": schema,
            "stream": False,
        }
        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise GenerationServiceError(f"Ollama generation request failed: {exc}") from exc

        body = response.json()
        generated = body.get("response")
        if not isinstance(generated, str):
            raise GenerationServiceError("Ollama generation response is missing 'response'.")
        try:
            parsed = json.loads(generated)
        except json.JSONDecodeError as exc:
            raise GenerationServiceError("Ollama generation response is not valid JSON.") from exc
        if not isinstance(parsed, dict):
            raise GenerationServiceError("Ollama generation response is not a JSON object.")

        logger.debug("ollama.generation_completed", model=self._model)
        return parsed
