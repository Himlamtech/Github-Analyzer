from __future__ import annotations
import asyncio
from typing import Dict, Any
import structlog
from src.domain.entities.ai_task import AITask
from src.domain.exceptions.ai_exceptions import AIProcessingError

logger = structlog.get_logger(__name__)

class ProcessAITaskUseCase:
    """
    UseCase responsible for orchestrating the AI analysis pipeline.
    It coordinates fetching repo data, splitting text, embedding, and LLM inference.
    """
    def __init__(self, llm_adapter, vector_store, github_client):
        self.llm_adapter = llm_adapter
        self.vector_store = vector_store
        self.github_client = github_client

    async def execute(self, task: AITask) -> AITask:
        log = logger.bind(task_id=task.task_id, repo=str(task.repository_url))
        log.info("Starting AI task processing")
        
        try:
            task.mark_processing()
            
            # Step 1: Fetch repository metadata
            log.debug("Fetching repository metadata")
            repo_data = await self.github_client.fetch_repo_details(str(task.repository_url))
            
            # Step 2: Extract chunks and embed them
            log.debug("Extracting readme and embedding chunks")
            readme_content = repo_data.get("readme", "")
            if readme_content:
                chunks = self._chunk_text(readme_content)
                await self.vector_store.store_documents(task.task_id, chunks)

            # Step 3: Call LLM for summarization
            log.debug("Calling LLM for code analysis")
            prompt = f"Analyze the following repository:\n{readme_content[:2000]}"
            summary = await self.llm_adapter.generate_completion(prompt)
            
            # Step 4: Finalize
            task.mark_completed(summary=summary, data={"repo_metrics": repo_data})
            log.info("Task completed successfully")
            
        except Exception as e:
            log.error("Task processing failed", error=str(e))
            task.mark_failed(str(e))
            raise AIProcessingError(f"Failed to process task {task.task_id}", details={"error": str(e)})
            
        return task

    def _chunk_text(self, text: str, chunk_size: int = 500) -> list[str]:
        words = text.split()
        return [" ".join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)]
