from __future__ import annotations
from pydantic import BaseModel, HttpUrl, Field
from typing import List, Optional

class AIAnalysisRequestDTO(BaseModel):
    repository_url: HttpUrl = Field(..., description="Target repository to analyze")
    analysis_depth: str = Field(default="standard", description="standard or deep")
    focus_areas: List[str] = Field(default_factory=list, description="e.g., security, performance")

class AIAnalysisResponseDTO(BaseModel):
    task_id: str
    status: str
    message: str
    estimated_time_seconds: Optional[int] = None
