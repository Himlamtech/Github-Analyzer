"""Ollama-backed embedding service for semantic reranking."""

from __future__ import annotations

from collections.abc import Sequence  # noqa: TC003

import httpx
import structlog

from src.domain.exceptions import EmbeddingServiceError

logger = structlog.get_logger(__name__)


class OllamaEmbeddingService:
    """Generate text embeddings through the Ollama HTTP API."""

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

    async def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        """Return one embedding vector per input text."""
        if not texts:
            return []

        url = f"{self._base_url}/api/embed"
        payload = {"model": self._model, "input": list(texts)}
        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise EmbeddingServiceError(f"Ollama embedding request failed: {exc}") from exc

        body = response.json()
        embeddings = body.get("embeddings")
        if not isinstance(embeddings, list):
            raise EmbeddingServiceError("Ollama embedding response is missing 'embeddings'.")

        vectors: list[list[float]] = []
        for embedding in embeddings:
            if not isinstance(embedding, list):
                raise EmbeddingServiceError("Ollama embedding payload contains a non-list vector.")
            try:
                vectors.append([float(value) for value in embedding])
            except (TypeError, ValueError) as exc:
                raise EmbeddingServiceError(
                    "Ollama embedding payload contains a non-numeric value."
                ) from exc

        logger.debug("ollama.embeddings_generated", count=len(vectors), model=self._model)
        return vectors
