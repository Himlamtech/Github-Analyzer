from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import structlog

from src.presentation.api.routes.ai_routes import router as ai_router

logger = structlog.get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing AI Service components...")
    # Initialize Kafka, Redis, Qdrant here
    yield
    logger.info("Shutting down AI Service components...")
    # Clean up resources here

app = FastAPI(
    title="Github Analyzer - AI Service",
    description="Microservice for handling LLM and Vector Search tasks",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ai_router)

@app.get("/health", tags=["System"])
def health_check():
    """Liveness probe for Kubernetes/Docker Compose."""
    return {"status": "ok", "service": "ai-service"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.presentation.api.main:app", host="0.0.0.0", port=8000, reload=True)
