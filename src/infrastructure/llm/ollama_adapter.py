from __future__ import annotations
import httpx
import structlog
import asyncio
from typing import Optional, AsyncGenerator
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from src.domain.exceptions.ai_exceptions import ModelTimeoutError, AIProcessingError

logger = structlog.get_logger(__name__)

class OllamaAdapter:
    """Adapter for interacting with local Ollama instance with robust retries."""
    
    def __init__(self, base_url: str = "http://localhost:11434", default_model: str = "llama3"):
        self.base_url = base_url.rstrip("/")
        self.default_model = default_model
        # Increased timeouts for heavy models
        self.timeout = httpx.Timeout(60.0, connect=10.0)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        reraise=True
    )
    async def generate_completion(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        log = logger.bind(model=self.default_model)
        log.info("Sending completion request to Ollama (with retry logic)")
        
        payload = {"model": self.default_model, "prompt": prompt, "stream": False}
        if system_prompt:
            payload["system"] = system_prompt
            
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(f"{self.base_url}/api/generate", json=payload)
                response.raise_for_status()
                return response.json().get("response", "")
        except httpx.TimeoutException as e:
            log.warning("Ollama request timed out, will retry if attempts remain")
            raise ModelTimeoutError("Ollama model timed out", details={"error": str(e)})
        except Exception as e:
            log.exception("Ollama request failed")
            raise AIProcessingError("Ollama error", details={"error": str(e)})

    async def generate_stream(self, prompt: str) -> AsyncGenerator[str, None]:
        payload = {"model": self.default_model, "prompt": prompt, "stream": True}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream("POST", f"{self.base_url}/api/generate", json=payload) as response:
                response.raise_for_status()
                async for chunk in response.aiter_lines():
                    if chunk:
                        import json
                        yield json.loads(chunk).get("response", "")
