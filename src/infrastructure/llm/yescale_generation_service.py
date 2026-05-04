"""Yescale-backed structured generation service."""

from __future__ import annotations

import json
from typing import Any

import httpx
import structlog

from src.domain.exceptions import GenerationServiceError

logger = structlog.get_logger(__name__)


class YescaleGenerationService:
    """Generate structured JSON from a prompt using Yescale's Gemini endpoint."""

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        api_key: str,
        timeout_seconds: float,
        temperature: float = 0.7,
        max_output_tokens: int = 1024,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._api_key = api_key.strip()
        self._timeout_seconds = timeout_seconds
        self._temperature = temperature
        self._max_output_tokens = max_output_tokens

    async def generate_json(
        self,
        *,
        prompt: str,
        system_prompt: str,
        schema: dict[str, Any],
    ) -> dict[str, Any]:
        """Return a JSON object produced according to the provided schema."""
        url = f"{self._base_url}/models/{self._model}:generateContent"
        payload = {
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {
                            "text": _build_json_prompt(prompt=prompt, schema=schema),
                        }
                    ],
                }
            ],
            "generationConfig": {
                "temperature": self._temperature,
                "maxOutputTokens": self._max_output_tokens,
                "responseMimeType": "application/json",
            },
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._api_key}",
        }
        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise GenerationServiceError(f"Yescale generation request failed: {exc}") from exc

        try:
            body = response.json()
        except ValueError as exc:
            raise GenerationServiceError("Yescale generation response is not JSON.") from exc
        if not isinstance(body, dict):
            raise GenerationServiceError("Yescale generation response is not a JSON object.")

        candidate_text = _extract_candidate_text(body)
        parsed = _parse_json_object(candidate_text)

        logger.debug("yescale.generation_completed", model=self._model)
        return parsed


def _build_json_prompt(*, prompt: str, schema: dict[str, Any]) -> str:
    schema_text = json.dumps(schema, ensure_ascii=False, separators=(",", ":"))
    return "\n\n".join(
        [
            prompt.strip(),
            f"Return only a single valid JSON object matching this schema: {schema_text}.",
            "Do not include markdown fences, commentary, or extra text.",
        ]
    )


def _extract_candidate_text(body: dict[str, Any]) -> str:
    candidates = body.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise GenerationServiceError("Yescale generation response is missing candidate text.")

    candidate = candidates[0]
    if not isinstance(candidate, dict):
        raise GenerationServiceError("Yescale generation response has an invalid candidate.")

    content = candidate.get("content")
    if not isinstance(content, dict):
        raise GenerationServiceError("Yescale generation response is missing candidate content.")

    parts = content.get("parts")
    if not isinstance(parts, list) or not parts:
        raise GenerationServiceError("Yescale generation response is missing candidate text.")

    texts: list[str] = []
    for part in parts:
        if not isinstance(part, dict):
            continue
        text = part.get("text")
        if isinstance(text, str) and text.strip():
            texts.append(text.strip())

    if not texts:
        raise GenerationServiceError("Yescale generation response is missing candidate text.")

    return "\n".join(texts).strip()


def _parse_json_object(text: str) -> dict[str, Any]:
    normalized = _strip_markdown_fences(text.strip())
    try:
        parsed = json.loads(normalized)
    except json.JSONDecodeError as first_exc:
        extracted = _extract_first_json_object(normalized)
        if extracted is None:
            raise GenerationServiceError(
                "Yescale generation response is not valid JSON."
            ) from first_exc
        try:
            parsed = json.loads(extracted)
        except json.JSONDecodeError as exc:
            raise GenerationServiceError("Yescale generation response is not valid JSON.") from exc

    if not isinstance(parsed, dict):
        raise GenerationServiceError("Yescale generation response is not a JSON object.")
    return parsed


def _strip_markdown_fences(text: str) -> str:
    lines = text.splitlines()
    if not lines:
        return text

    if lines[0].strip().startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _extract_first_json_object(text: str) -> str | None:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    return text[start : end + 1]
