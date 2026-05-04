"""Unit tests for the Yescale-backed structured generation adapter."""

from __future__ import annotations

from httpx import Response
import pytest
import respx

from src.domain.exceptions import GenerationServiceError
from src.infrastructure.llm.yescale_generation_service import YescaleGenerationService


def _service() -> YescaleGenerationService:
    return YescaleGenerationService(
        base_url="https://api.yescale.test/v1beta",
        model="gemini-test",
        api_key="test-key",
        timeout_seconds=5.0,
    )


@pytest.mark.asyncio
@respx.mock
async def test_generate_json_posts_bearer_request_and_parses_candidate_text() -> None:
    service = _service()
    route = respx.post("https://api.yescale.test/v1beta/models/gemini-test:generateContent").mock(
        return_value=Response(
            200,
            json={
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {
                                    "text": (
                                        '{"answer":"browser-use is leading.",'
                                        '"follow_up_questions":["Compare it","Show related"]}'
                                    )
                                }
                            ]
                        }
                    }
                ]
            },
        )
    )

    result = await service.generate_json(
        prompt="Question: repo nao hot?",
        system_prompt="Answer from evidence only.",
        schema={
            "type": "object",
            "properties": {"answer": {"type": "string"}},
            "required": ["answer"],
        },
    )

    assert route.called
    request = route.calls.last.request
    assert request.headers["Authorization"] == "Bearer test-key"
    payload = request.read().decode()
    assert '"model"' not in payload
    assert "Question: repo nao hot?" in payload
    assert "Return only a single valid JSON object" in payload
    assert result == {
        "answer": "browser-use is leading.",
        "follow_up_questions": ["Compare it", "Show related"],
    }


@pytest.mark.asyncio
@respx.mock
async def test_generate_json_strips_markdown_fences_from_model_text() -> None:
    service = _service()
    respx.post("https://api.yescale.test/v1beta/models/gemini-test:generateContent").mock(
        return_value=Response(
            200,
            json={
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {
                                    "text": (
                                        '```json\n{"answer":"ok",'
                                        '"follow_up_questions":["next","more"]}\n```'
                                    )
                                }
                            ]
                        }
                    }
                ]
            },
        )
    )

    result = await service.generate_json(
        prompt="Question: test",
        system_prompt="Return JSON.",
        schema={"type": "object"},
    )

    assert result["answer"] == "ok"


@pytest.mark.asyncio
@respx.mock
async def test_generate_json_raises_generation_error_on_http_failure() -> None:
    service = _service()
    respx.post("https://api.yescale.test/v1beta/models/gemini-test:generateContent").mock(
        return_value=Response(401, json={"error": {"message": "bad key"}})
    )

    with pytest.raises(GenerationServiceError, match="Yescale generation request failed"):
        await service.generate_json(
            prompt="Question: test",
            system_prompt="Return JSON.",
            schema={"type": "object"},
        )


@pytest.mark.asyncio
@respx.mock
async def test_generate_json_raises_generation_error_on_invalid_payload() -> None:
    service = _service()
    respx.post("https://api.yescale.test/v1beta/models/gemini-test:generateContent").mock(
        return_value=Response(200, json={"candidates": [{"content": {"parts": []}}]})
    )

    with pytest.raises(GenerationServiceError, match="missing candidate text"):
        await service.generate_json(
            prompt="Question: test",
            system_prompt="Return JSON.",
            schema={"type": "object"},
        )
