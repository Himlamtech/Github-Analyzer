"""Domain exception hierarchy for the GitHub AI Trend Analyzer.

All application-level exceptions derive from DomainException so that
infrastructure and presentation layers can catch a single base type while
still distinguishing specific error categories when needed.
"""

from __future__ import annotations


class DomainException(Exception):  # noqa: N818
    """Base exception for all domain errors.

    Args:
        message: Human-readable description of the error.
        code: Optional machine-readable error code for structured logging.
    """

    def __init__(self, message: str, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.code = code or self.__class__.__name__

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(message={self.message!r}, code={self.code!r})"


# ── Validation ────────────────────────────────────────────────────────────────


class ValidationError(DomainException):
    """Raised when a domain invariant or value-object constraint is violated."""


class InvalidEventTypeError(ValidationError):
    """Raised when an unknown GitHub event type is encountered."""


class InvalidRepositoryIdError(ValidationError):
    """Raised when a repository identifier fails format validation."""


# ── GitHub API ────────────────────────────────────────────────────────────────


class GitHubAPIError(DomainException):
    """Base for all GitHub API integration errors."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class RateLimitExceededError(GitHubAPIError):
    """All available tokens have hit their rate limit ceiling."""

    def __init__(self, reset_at_seconds: float) -> None:
        super().__init__(
            f"All GitHub tokens exhausted. Earliest reset in {reset_at_seconds:.0f}s.",
            status_code=429,
        )
        self.reset_at_seconds = reset_at_seconds


class GitHubAuthenticationError(GitHubAPIError):
    """Token is invalid or has insufficient permissions."""

    def __init__(self) -> None:
        super().__init__("GitHub token authentication failed.", status_code=401)


class GitHubNotFoundError(GitHubAPIError):
    """Requested GitHub resource does not exist."""

    def __init__(self, resource: str) -> None:
        super().__init__(f"GitHub resource not found: {resource}", status_code=404)


# ── Kafka ─────────────────────────────────────────────────────────────────────


class KafkaError(DomainException):
    """Base for all Kafka integration errors."""


class ProducerException(KafkaError):  # noqa: N818
    """Failed to publish a message to Kafka."""


class ConsumerException(KafkaError):  # noqa: N818
    """Failed to consume a message from Kafka."""


class TopicAdminException(KafkaError):  # noqa: N818
    """Failed to create or verify a Kafka topic."""


# ── Storage ───────────────────────────────────────────────────────────────────


class StorageError(DomainException):
    """Base for all storage-layer errors."""


class ParquetWriteError(StorageError):
    """Failed to write data to the Parquet archive."""


class ClickHouseWriteError(StorageError):
    """Failed to insert data into ClickHouse."""


class ClickHouseConnectionError(StorageError):
    """Failed to connect to ClickHouse."""


class ClickHouseBackfillError(StorageError):
    """Failed to bootstrap ClickHouse tables from the local Parquet archive."""


class DuckDBQueryError(StorageError):
    """Failed to execute a DuckDB analytical query."""


# ── Spark ─────────────────────────────────────────────────────────────────────


class SparkJobError(DomainException):
    """Spark structured streaming or batch job failed."""


# ── Metadata Sync ──────────────────────────────────────────────────────────────


class RepoMetadataSyncError(StorageError):
    """Failed to sync repo metadata from JSON files to ClickHouse."""


class RepoMetadataParseError(ValidationError):
    """Failed to parse a repo metadata JSON file into RepoMetadata."""


class DashboardQueryError(StorageError):
    """A dashboard analytical query against ClickHouse failed."""


# ── AI Search ────────────────────────────────────────────────────────────────


class AISearchError(StorageError):
    """AI-powered repository search failed."""


class AIInsightError(StorageError):
    """AI-generated repository insight workflow failed."""


class RepoInsightNotFoundError(AIInsightError):
    """Requested repository insight context does not exist."""


class EmbeddingServiceError(DomainException):
    """Semantic embedding request failed."""


class GenerationServiceError(DomainException):
    """Structured generation request failed."""
