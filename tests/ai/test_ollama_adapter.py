import pytest
from unittest.mock import AsyncMock, patch
from src.infrastructure.llm.ollama_adapter import OllamaAdapter
from src.domain.exceptions.ai_exceptions import ModelTimeoutError
import httpx

@pytest.fixture
def adapter():
    return OllamaAdapter(base_url="http://test-ollama:11434")

@pytest.mark.asyncio
async def test_ollama_generate_completion_success(adapter):
    mock_response = AsyncMock()
    mock_response.json.return_value = {"response": "Mocked AI output"}
    mock_response.raise_for_status.return_value = None

    with patch("httpx.AsyncClient.post", return_value=mock_response):
        result = await adapter.generate_completion("Hello")
        assert result == "Mocked AI output"

@pytest.mark.asyncio
async def test_ollama_timeout_handling(adapter):
    with patch("httpx.AsyncClient.post", side_effect=httpx.TimeoutException("Timeout")):
        with pytest.raises(ModelTimeoutError):
            await adapter.generate_completion("Long prompt")
