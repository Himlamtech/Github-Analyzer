from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.responses import StreamingResponse
import uuid
import structlog
from src.application.dto.ai_requests import AIAnalysisRequestDTO, AIAnalysisResponseDTO
from src.domain.entities.ai_task import AITask

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1/ai", tags=["AI Integration"])

# Pseudo-dependency for demonstration
def get_process_usecase():
    return None

@router.post("/analyze", response_model=AIAnalysisResponseDTO, status_code=status.HTTP_202_ACCEPTED)
async def submit_analysis_task(
    request: AIAnalysisRequestDTO,
    background_tasks: BackgroundTasks,
    usecase = Depends(get_process_usecase)
):
    """
    Submit a GitHub repository for AI-powered analysis.
    The task is processed asynchronously in the background.
    """
    task_id = f"task_{uuid.uuid4().hex[:8]}"
    logger.info("Received analysis request", task_id=task_id, url=str(request.repository_url))
    
    task = AITask(task_id=task_id, repository_url=request.repository_url)
    
    # In a real app, we would push this to Redis/Kafka instead of BackgroundTasks
    # background_tasks.add_task(usecase.execute, task)
    
    return AIAnalysisResponseDTO(
        task_id=task_id,
        status="accepted",
        message="Task queued for processing.",
        estimated_time_seconds=45
    )

@router.get("/task/{task_id}", response_model=AITask)
async def get_task_status(task_id: str):
    """Retrieve the current status and results of an AI task."""
    logger.debug("Checking task status", task_id=task_id)
    # Mock lookup
    raise HTTPException(status_code=404, detail="Task not found")

@router.post("/chat/stream")
async def stream_chat_response(query: str):
    """Stream an answer from Ollama directly to the client."""
    from src.infrastructure.llm.ollama_adapter import OllamaAdapter
    adapter = OllamaAdapter()
    return StreamingResponse(adapter.generate_stream(query), media_type="text/event-stream")
