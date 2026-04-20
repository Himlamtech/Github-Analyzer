"""Unit tests for the domain exception hierarchy."""

from __future__ import annotations

import pytest

from src.domain.exceptions import (
    ClickHouseWriteError,
    DomainException,
    GitHubAPIError,
    InvalidEventTypeError,
    InvalidRepositoryIdError,
    RateLimitExceededError,
    ValidationError,
)


class TestDomainException:
    """Tests for DomainException base class."""

    def test_domain_exception_stores_message(self) -> None:
        """DomainException must expose the original message via .message."""
        exc = DomainException("something went wrong")
        assert exc.message == "something went wrong"

    def test_domain_exception_default_code_is_class_name(self) -> None:
        """When no code is provided, code defaults to the class name."""
        exc = DomainException("error")
        assert exc.code == "DomainException"

    def test_domain_exception_custom_code_is_stored(self) -> None:
        """Explicit code parameter is stored as-is."""
        exc = DomainException("error", code="ERR_001")
        assert exc.code == "ERR_001"

    def test_domain_exception_repr_includes_message_and_code(self) -> None:
        """__repr__ must include both message and code for structured logging."""
        exc = DomainException("test error", code="E42")
        repr_str = repr(exc)
        assert "test error" in repr_str
        assert "E42" in repr_str

    def test_domain_exception_is_an_exception(self) -> None:
        """DomainException must be raisable and catchable as Exception."""
        with pytest.raises(DomainException):
            raise DomainException("raised domain error")


class TestValidationError:
    """Tests for ValidationError and its subtypes."""

    def test_validation_error_is_domain_exception(self) -> None:
        """ValidationError must inherit from DomainException."""
        exc = ValidationError("invalid value")
        assert isinstance(exc, DomainException)

    def test_invalid_event_type_error_is_validation_error(self) -> None:
        """InvalidEventTypeError must inherit from ValidationError."""
        exc = InvalidEventTypeError("bad type")
        assert isinstance(exc, ValidationError)

    def test_invalid_repository_id_error_is_validation_error(self) -> None:
        """InvalidRepositoryIdError must inherit from ValidationError."""
        exc = InvalidRepositoryIdError("bad id")
        assert isinstance(exc, ValidationError)

    def test_catch_validation_error_by_domain_exception(self) -> None:
        """ValidationError can be caught by DomainException handler."""
        with pytest.raises(DomainException):
            raise ValidationError("caught as DomainException")


class TestGitHubAPIError:
    """Tests for GitHubAPIError and its subtypes."""

    def test_github_api_error_stores_status_code(self) -> None:
        """GitHubAPIError must expose the HTTP status code."""
        exc = GitHubAPIError("not found", status_code=404)
        assert exc.status_code == 404

    def test_github_api_error_none_status_code(self) -> None:
        """GitHubAPIError allows None status code for non-HTTP errors."""
        exc = GitHubAPIError("unknown error")
        assert exc.status_code is None

    def test_rate_limit_exceeded_error_status_code_is_429(self) -> None:
        """RateLimitExceededError must set status_code to 429."""
        exc = RateLimitExceededError(reset_at_seconds=120.0)
        assert exc.status_code == 429

    def test_rate_limit_exceeded_error_message_contains_reset_time(self) -> None:
        """RateLimitExceededError message must include the reset time."""
        exc = RateLimitExceededError(reset_at_seconds=300.0)
        assert "300" in exc.message

    def test_rate_limit_exceeded_error_is_github_api_error(self) -> None:
        """RateLimitExceededError must inherit from GitHubAPIError."""
        exc = RateLimitExceededError(reset_at_seconds=60.0)
        assert isinstance(exc, GitHubAPIError)


class TestClickHouseWriteError:
    """Tests for ClickHouseWriteError."""

    def test_clickhouse_write_error_is_domain_exception(self) -> None:
        """ClickHouseWriteError must inherit from DomainException."""
        exc = ClickHouseWriteError("insert failed")
        assert isinstance(exc, DomainException)

    def test_clickhouse_write_error_message_is_stored(self) -> None:
        """ClickHouseWriteError must expose the error message."""
        exc = ClickHouseWriteError("batch insert failed: timeout")
        assert "batch insert failed" in exc.message
