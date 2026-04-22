from __future__ import annotations
from enum import Enum
from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, Dict, Any, List
from datetime import datetime

class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class RepoMetrics(BaseModel):
    stars: int = Field(default=0, ge=0)
    forks: int = Field(default=0, ge=0)
    watchers: int = Field(default=0, ge=0)
    open_issues: int = Field(default=0, ge=0)

class AITask(BaseModel):
    task_id: str = Field(..., description="Unique identifier for the task")
    repository_url: HttpUrl = Field(..., description="URL of the GitHub repository")
    status: TaskStatus = Field(default=TaskStatus.PENDING)
    metrics: Optional[RepoMetrics] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    result_summary: Optional[str] = None
    structured_data: Optional[Dict[str, Any]] = None

    def mark_processing(self) -> None:
        self.status = TaskStatus.PROCESSING
        self.updated_at = datetime.utcnow()

    def mark_completed(self, summary: str, data: Dict[str, Any]) -> None:
        self.status = TaskStatus.COMPLETED
        self.result_summary = summary
        self.structured_data = data
        self.updated_at = datetime.utcnow()

    def mark_failed(self, error: str) -> None:
        self.status = TaskStatus.FAILED
        self.result_summary = f"Error: {error}"
        self.updated_at = datetime.utcnow()
