from __future__ import annotations
import httpx
import structlog
import asyncio
from typing import Optional, AsyncGenerator
from src.domain.exceptions.ai_exceptions import ModelTimeoutError, AIProcessingError

logger = structlog.get_logger(__name__)

class OllamaAdapter:
    """Adapter for interacting with local Ollama instance."""
    
    def __init__(self, base_url: str = "http://localhost:11434", default_model: str = "llama3"):
        self.base_url = base_url.rstrip("/")
        self.default_model = default_model
        self.timeout = httpx.Timeout(30.0, connect=5.0)

    async def generate_completion(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generate a single string response from the LLM."""
        log = logger.bind(model=self.default_model)
        log.info("Sending completion request to Ollama")
        
        payload = {
            "model": self.default_model,
            "prompt": prompt,
            "stream": False
        }
        if system_prompt:
            payload["system"] = system_prompt
            
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(f"{self.base_url}/api/generate", json=payload)
                response.raise_for_status()
                data = response.json()
                return data.get("response", "")
        except httpx.TimeoutException as e:
            log.error("Ollama request timed out")
            raise ModelTimeoutError("Ollama model timed out", details={"error": str(e)})
        except httpx.HTTPStatusError as e:
            log.error("Ollama returned HTTP error", status_code=e.response.status_code)
            raise AIProcessingError("HTTP Error from Ollama", details={"status": e.response.status_code})
        except Exception as e:
            log.exception("Unexpected error communicating with Ollama")
            raise AIProcessingError("Unexpected Ollama error", details={"error": str(e)})

    async def generate_stream(self, prompt: str) -> AsyncGenerator[str, None]:
        """Stream the response from Ollama token by token."""
        payload = {
            "model": self.default_model,
            "prompt": prompt,
            "stream": True
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream("POST", f"{self.base_url}/api/generate", json=payload) as response:
                response.raise_for_status()
                async for chunk in response.aiter_lines():
                    if chunk:
                        import json
                        data = json.loads(chunk)
                        yield data.get("response", "")
