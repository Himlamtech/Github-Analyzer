"""Data Transfer Objects for GitHub events.

DTOs cross layer boundaries without exposing domain internals.
``GithubEventInputDTO``: raw API payload → validated structure for use cases.
``GithubEventOutputDTO``: domain entity → serialised form for Kafka / API.
``RepoStarCountDTO`` / ``HourlyActivityDTO``: query result shapes for DuckDB.
"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class GithubEventInputDTO(BaseModel):
    """Validated representation of a raw GitHub API event object.

    Constructed by the event mapper in the Infrastructure layer.
    The Use Case validates and maps this to a domain entity.
    """

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    event_id: str = Field(..., min_length=1)
    event_type: str = Field(..., min_length=1)
    actor_id: int = Field(..., gt=0)
    actor_login: str = Field(..., min_length=1)
    repo_id: int = Field(..., gt=0)
    repo_name: str = Field(..., pattern=r"^[^/]+/[^/]+$")
    payload: dict[str, object] = Field(default_factory=dict)
    repo_stargazers_count: int = Field(default=0, ge=0)
    repo_primary_language: str = Field(default="")
    repo_topics: list[str] = Field(default_factory=list)
    repo_description: str = Field(default="")
    repo_full_metadata_json: str = Field(default="")
    repo_readme_text: str = Field(default="")
    repo_issues_json: str = Field(default="")
    created_at: datetime
    public: bool = True

    @field_validator("created_at", mode="before")
    @classmethod
    def parse_iso_datetime(cls, v: object) -> datetime:
        """Accept both ISO-8601 strings and datetime objects."""
        if isinstance(v, datetime):
            return v
        if isinstance(v, str):
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        raise ValueError(f"Cannot parse datetime from {v!r}")


class GithubEventOutputDTO(BaseModel):
    """Serialisable event shape published to Kafka and returned by the API.

    This is the wire format consumed by downstream Spark jobs.
    All field names match the Spark StructType defined in ``schemas.py``.
    """

    model_config = ConfigDict(frozen=True)

    event_id: str
    event_type: str
    actor_id: int
    actor_login: str
    repo_id: int
    repo_name: str
    event_date: str  # YYYY-MM-DD — pre-computed for Parquet partitioning
    created_at: str  # ISO-8601 UTC string
    payload_json: str  # JSON-serialised payload
    repo_stargazers_count: int = 0
    repo_primary_language: str = ""
    repo_topics: list[str] = Field(default_factory=list)
    repo_description: str = ""
    repo_full_metadata_json: str = ""
    repo_readme_text: str = ""
    repo_issues_json: str = ""


class RepoStarCountDTO(BaseModel):
    """Result shape for top-repos-by-stars DuckDB query."""

    model_config = ConfigDict(frozen=True)

    repo_name: str
    event_date: date
    star_count: int


class HourlyActivityDTO(BaseModel):
    """Result shape for hourly-activity DuckDB query."""

    model_config = ConfigDict(frozen=True)

    hour: int = Field(..., ge=0, le=23)
    event_count: int = Field(..., ge=0)
