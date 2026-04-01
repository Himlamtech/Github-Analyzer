"""DTOs for repository metadata exchanged across backend layers."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RepoMetadataDTO(BaseModel):
    """Normalized repository metadata for dashboard and AI responses."""

    model_config = ConfigDict(frozen=True)

    repo_id: int = Field(..., ge=0)
    repo_full_name: str
    repo_name: str
    html_url: str
    description: str = ""
    primary_language: str = ""
    topics: list[str]
    category: str = "Other"
    stargazers_count: int = Field(..., ge=0)
    watchers_count: int = Field(..., ge=0)
    forks_count: int = Field(..., ge=0)
    open_issues_count: int = Field(..., ge=0)
    subscribers_count: int = Field(..., ge=0)
    owner_login: str = ""
    owner_avatar_url: str = ""
    license_name: str = ""
    github_created_at: datetime
    github_pushed_at: datetime
    rank: int = Field(default=0, ge=0)
