"""Domain exception hierarchy for the GitHub AI Trend Analyzer."""

from __future__ import annotations


class DomainException(Exception):
    """Base exception for all domain-specific failures."""

    def __init__(self, message: str, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.code = code or self.__class__.__name__

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(message={self.message!r}, code={self.code!r})"


class ValidationError(DomainException):
    """Raised when an input or invariant is invalid."""


class ClickHouseConnectionError(DomainException):
    """Raised when ClickHouse cannot be reached."""


class ClickHouseBackfillError(DomainException):
    """Raised when the ClickHouse bootstrap flow fails."""


class ClickHouseWriteError(DomainException):
    """Raised when ClickHouse insert/update operations fail."""


class DashboardQueryError(DomainException):
    """Raised when a dashboard analytical query fails."""


class AISearchError(DomainException):
    """Raised when AI repository search fails."""


class AIInsightError(DomainException):
    """Raised when AI insight generation or context retrieval fails."""


class RepoInsightNotFoundError(DomainException):
    """Raised when the requested repository context does not exist."""


class EmbeddingServiceError(DomainException):
    """Raised when semantic embedding generation fails."""


class GenerationServiceError(DomainException):
    """Raised when structured generation fails."""
