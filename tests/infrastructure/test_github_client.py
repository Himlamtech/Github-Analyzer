"""Unit tests for GitHubClient — all HTTP calls are mocked via respx."""

from __future__ import annotations

import httpx
import pytest
import respx

from src.domain.exceptions import (
    GitHubAuthenticationError,
    GitHubNotFoundError,
    RateLimitExceededError,
)
from src.infrastructure.github.client import GitHubClient, _TokenState
from src.infrastructure.observability.metrics import (
    GITHUB_API_RATE_LIMIT_REMAINING,
    GITHUB_API_TOKEN_CONFIGURED_INFO,
    GITHUB_API_TOKEN_EXHAUSTED,
)


class TestTokenState:
    """Tests for per-token rate-limit state tracking."""

    def test_is_not_exhausted_with_full_quota(self) -> None:
        """Token with remaining=5000 should not be considered exhausted."""
        state = _TokenState(token="tok", index=0, remaining=5000)
        assert state.is_exhausted() is False

    def test_is_exhausted_when_below_threshold(self) -> None:
        """Token with remaining<100 and reset in future should be skipped."""
        import time

        state = _TokenState(
            token="tok",
            index=0,
            remaining=50,
            reset_at=time.monotonic() + 3600,  # reset in 1 hour
        )
        assert state.is_exhausted() is True

    def test_is_not_exhausted_after_reset_window(self) -> None:
        """Token past its reset_at should no longer be exhausted."""
        import time

        state = _TokenState(
            token="tok",
            index=0,
            remaining=50,
            reset_at=time.monotonic() - 1,  # reset already passed
        )
        assert state.is_exhausted() is False


class TestGitHubClientTokenPool:
    """Tests for round-robin token selection and circuit breaker."""

    def test_initializes_metrics_for_every_configured_token(self) -> None:
        client = GitHubClient(tokens=["tok1", "tok2", "tok3"])

        assert len(client._states) == 3
        assert GITHUB_API_TOKEN_CONFIGURED_INFO.labels(token_index=0)._value.get() == 1
        assert GITHUB_API_TOKEN_CONFIGURED_INFO.labels(token_index=1)._value.get() == 1
        assert GITHUB_API_TOKEN_CONFIGURED_INFO.labels(token_index=2)._value.get() == 1
        assert GITHUB_API_RATE_LIMIT_REMAINING.labels(token_index=2)._value.get() == 5000
        assert GITHUB_API_TOKEN_EXHAUSTED.labels(token_index=1)._value.get() == 0

    def test_raises_rate_limit_error_when_all_tokens_exhausted(self) -> None:
        """All-exhausted token pool must raise RateLimitExceededError."""
        import time

        client = GitHubClient(tokens=["tok1", "tok2"])
        for state in client._states:
            state.remaining = 0
            state.reset_at = time.monotonic() + 3600

        with pytest.raises(RateLimitExceededError):
            client._next_token_state()

    def test_selects_non_exhausted_token_when_first_is_exhausted(self) -> None:
        """Should skip exhausted token and return the next available one."""
        import time

        client = GitHubClient(tokens=["tok1", "tok2"])
        # Exhaust first token
        client._states[0].remaining = 0
        client._states[0].reset_at = time.monotonic() + 3600
        # Second token is healthy
        client._states[1].remaining = 5000

        selected = client._next_token_state()
        assert selected.token == "tok2"


class TestGitHubClientHTTP:
    """Tests for HTTP response handling via mocked httpx."""

    @respx.mock
    async def test_fetch_events_returns_events_on_200(self) -> None:
        """Happy path: 200 response returns parsed event list."""
        events = [{"id": "1", "type": "WatchEvent"}]
        respx.get("https://api.github.com/events").mock(
            return_value=httpx.Response(
                200,
                json=events,
                headers={
                    "x-ratelimit-remaining": "4999",
                    "x-ratelimit-reset": "9999999999",
                    "etag": '"abc123"',
                },
            )
        )
        client = GitHubClient(tokens=["fake_token"])
        result = await client.fetch_events()
        assert result == events

    @respx.mock
    async def test_fetch_events_enriches_with_repo_metadata_without_readme_or_issues_calls(
        self,
    ) -> None:
        """Event enrichment must stay bounded to one repo metadata lookup per repo."""
        events = [
            {
                "id": "1",
                "type": "WatchEvent",
                "repo": {"name": "openai/codex"},
            }
        ]
        respx.get("https://api.github.com/events").mock(
            return_value=httpx.Response(
                200,
                json=events,
                headers={
                    "x-ratelimit-remaining": "4999",
                    "x-ratelimit-reset": "9999999999",
                },
            )
        )
        repo_route = respx.get("https://api.github.com/repos/openai/codex").mock(
            return_value=httpx.Response(
                200,
                json={
                    "full_name": "openai/codex",
                    "description": "AI coding agent",
                    "topics": ["ai", "agent"],
                    "stargazers_count": 1000,
                },
                headers={
                    "x-ratelimit-remaining": "4998",
                    "x-ratelimit-reset": "9999999999",
                },
            )
        )
        readme_route = respx.get("https://api.github.com/repos/openai/codex/readme").mock(
            return_value=httpx.Response(200, json={"content": "", "encoding": "base64"})
        )
        issues_route = respx.get(
            "https://api.github.com/repos/openai/codex/issues?state=all&per_page=100&page=1"
        ).mock(return_value=httpx.Response(200, json=[]))

        client = GitHubClient(tokens=["fake_token"])

        result = await client.fetch_events()

        assert repo_route.call_count == 1
        assert readme_route.call_count == 0
        assert issues_route.call_count == 0
        assert result[0]["_full_repo"] == {
            "full_name": "openai/codex",
            "description": "AI coding agent",
            "topics": ["ai", "agent"],
            "stargazers_count": 1000,
        }
        assert result[0]["_repo_readme_text"] == ""
        assert result[0]["_repo_issues"] == []

    @respx.mock
    async def test_fetch_events_returns_empty_on_304(self) -> None:
        """304 Not Modified must return empty list (ETag cache hit)."""
        respx.get("https://api.github.com/events").mock(
            return_value=httpx.Response(
                304,
                headers={
                    "x-ratelimit-remaining": "4999",
                    "x-ratelimit-reset": "9999999999",
                },
            )
        )
        client = GitHubClient(tokens=["fake_token"])
        # Pre-set ETag so the 304 logic path is hit
        client._states[0].etag["/events"] = '"old_etag"'
        result = await client.fetch_events()
        assert result == []

    @respx.mock
    async def test_fetch_events_raises_auth_error_on_401(self) -> None:
        """401 response must raise GitHubAuthenticationError."""
        respx.get("https://api.github.com/events").mock(
            return_value=httpx.Response(401, json={"message": "Bad credentials"})
        )
        client = GitHubClient(tokens=["invalid_token"])
        with pytest.raises(GitHubAuthenticationError):
            await client.fetch_events()

    @respx.mock
    async def test_fetch_events_raises_not_found_on_404(self) -> None:
        """404 response must raise GitHubNotFoundError."""
        respx.get("https://api.github.com/events").mock(
            return_value=httpx.Response(404, json={"message": "Not Found"})
        )
        client = GitHubClient(tokens=["fake_token"])
        with pytest.raises(GitHubNotFoundError):
            await client.fetch_events()
