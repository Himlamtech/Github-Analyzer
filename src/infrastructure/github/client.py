"""Async GitHub Events API client with token pooling and lightweight enrichment.

Features:
- Round-robin token rotation via ``itertools.cycle``
- Per-token rate-limit state tracking (remaining + reset_at)
- Circuit breaker: skip exhausted tokens until their reset window passes
- ETag caching: send ``If-None-Match`` → handle 304 (no wasted quota)
- Tenacity retry: exponential back-off, max 3 attempts
- Connection pooling: ``httpx.Limits(max_connections=20)``
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
import itertools
import time
from typing import TYPE_CHECKING

import httpx
import structlog
from tenacity import (
    AsyncRetrying,
    RetryError,
    stop_after_attempt,
    wait_exponential,
)

from src.domain.exceptions import (
    GitHubAPIError,
    GitHubAuthenticationError,
    GitHubNotFoundError,
    RateLimitExceededError,
)
from src.infrastructure.github.repo_fetcher import map_repo_response
from src.infrastructure.observability.metrics import (
    GITHUB_API_RATE_LIMIT_REMAINING,
    GITHUB_API_RATE_LIMIT_RESET_AT_SECONDS,
    GITHUB_API_REQUESTS_TOTAL,
    GITHUB_API_TOKEN_CONFIGURED_INFO,
    GITHUB_API_TOKEN_EXHAUSTED,
)

logger = structlog.get_logger(__name__)

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator
    from datetime import date

_EVENTS_ENDPOINT = "/events"
_SEARCH_ENDPOINT = "/search/repositories"
_RATE_LIMIT_THRESHOLD = 100  # Skip token when remaining < this value
_REPO_CACHE_TTL: float = 3600.0  # Cache repo metadata for 1 hour
_ISSUES_PAGE_SIZE: int = 100
_SEARCH_PAGE_SIZE: int = 100


@dataclass
class _TokenState:
    """Mutable rate-limit state for a single GitHub API token."""

    token: str
    index: int
    remaining: int = 5000
    reset_at: float = field(default_factory=lambda: time.monotonic() + 3600)
    etag: dict[str, str] = field(default_factory=dict)  # endpoint → ETag value

    def is_exhausted(self) -> bool:
        """Return True if the token should be skipped until its reset window."""
        return self.remaining < _RATE_LIMIT_THRESHOLD and time.monotonic() < self.reset_at

    def update_from_headers(self, headers: httpx.Headers) -> None:
        """Update rate-limit state from GitHub response headers."""
        if remaining := headers.get("x-ratelimit-remaining"):
            self.remaining = int(remaining)
            GITHUB_API_RATE_LIMIT_REMAINING.labels(token_index=self.index).set(self.remaining)
        if reset_epoch := headers.get("x-ratelimit-reset"):
            reset_at_epoch = float(reset_epoch)
            self.reset_at = reset_at_epoch - time.time() + time.monotonic()
            GITHUB_API_RATE_LIMIT_RESET_AT_SECONDS.labels(token_index=self.index).set(
                reset_at_epoch
            )
        GITHUB_API_TOKEN_EXHAUSTED.labels(token_index=self.index).set(int(self.is_exhausted()))


class GitHubClient:
    """Async client for the GitHub public Events API.

    Args:
        tokens:   List of GitHub bearer tokens (at least one required).
        base_url: GitHub API base URL (overridable for testing).
    """

    def __init__(
        self,
        tokens: list[str],
        base_url: str = "https://api.github.com",
    ) -> None:
        if not tokens:
            raise ValueError("At least one GitHub API token is required.")
        self._states = [_TokenState(token=t, index=i) for i, t in enumerate(tokens)]
        self._cycle: itertools.cycle[_TokenState] = itertools.cycle(self._states)
        self._base_url = base_url.rstrip("/")
        # TTL cache: repo_full_name -> (metadata_dict, expires_at_unix)
        self._repo_cache: dict[str, tuple[dict[str, object], float]] = {}
        self._http_client = httpx.AsyncClient(
            base_url=self._base_url,
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
            timeout=httpx.Timeout(connect=5.0, read=30.0, write=10.0, pool=5.0),
            headers={
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            follow_redirects=True,
        )
        self._initialize_token_metrics()

    async def __aenter__(self) -> GitHubClient:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self._http_client.aclose()

    @staticmethod
    def _coerce_int(value: object) -> int:
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        if isinstance(value, str):
            try:
                return int(value)
            except ValueError:
                return 0
        return 0

    def _next_token_state(self) -> _TokenState:
        """Return the next non-exhausted token state via round-robin.

        Raises:
            RateLimitExceededError: If all tokens are currently exhausted.
        """
        attempts = len(self._states)
        for _ in range(attempts):
            state = next(self._cycle)
            if not state.is_exhausted():
                return state
        earliest_reset = min(s.reset_at for s in self._states)
        wait_seconds = max(0.0, earliest_reset - time.monotonic())
        raise RateLimitExceededError(reset_at_seconds=wait_seconds)

    def _initialize_token_metrics(self) -> None:
        """Emit baseline Prometheus series for every configured GitHub token."""
        for state in self._states:
            GITHUB_API_TOKEN_CONFIGURED_INFO.labels(token_index=state.index).set(1)
            GITHUB_API_RATE_LIMIT_REMAINING.labels(token_index=state.index).set(state.remaining)
            reset_at_epoch = time.time() + max(0.0, state.reset_at - time.monotonic())
            GITHUB_API_RATE_LIMIT_RESET_AT_SECONDS.labels(token_index=state.index).set(
                reset_at_epoch
            )
            GITHUB_API_TOKEN_EXHAUSTED.labels(token_index=state.index).set(0)

    async def _get(
        self, endpoint: str, state: _TokenState
    ) -> tuple[int, list[dict[str, object]] | None, httpx.Headers]:
        """Execute a single authenticated GET with ETag caching.

        Returns:
            Tuple of (status_code, parsed_body_or_None, response_headers).
        """
        request_headers: dict[str, str] = {
            "Authorization": f"Bearer {state.token}",
        }
        if cached_etag := state.etag.get(endpoint):
            request_headers["If-None-Match"] = cached_etag

        response = await self._http_client.get(endpoint, headers=request_headers)
        status = response.status_code
        GITHUB_API_REQUESTS_TOTAL.labels(token_index=state.index, status_code=str(status)).inc()
        state.update_from_headers(response.headers)

        if status == 304:
            # No new data — ETag matched, quota not consumed
            return status, None, response.headers

        if status == 401:
            raise GitHubAuthenticationError()

        if status == 404:
            raise GitHubNotFoundError(resource=endpoint)

        if status == 403 or status == 429:
            # Treat 403 with rate-limit headers as rate limiting
            wait = max(0.0, state.reset_at - time.monotonic())
            raise RateLimitExceededError(reset_at_seconds=wait)

        if not response.is_success:
            raise GitHubAPIError(
                f"GitHub API returned {status} for {endpoint}",
                status_code=status,
            )

        if etag := response.headers.get("etag"):
            state.etag[endpoint] = etag

        body: list[dict[str, object]] = response.json()
        return status, body, response.headers

    async def _get_object(
        self, endpoint: str, state: _TokenState
    ) -> tuple[int, object | None, httpx.Headers]:
        """Execute a GET for endpoints that return a single JSON object (not a list).

        Used for repository metadata lookups (``/repos/{owner}/{repo}``).

        Args:
            endpoint: API path relative to base URL.
            state:    Token state to use for auth and quota tracking.

        Returns:
            Tuple of (status_code, parsed_body_or_None, response_headers).
        """
        response = await self._http_client.get(
            endpoint,
            headers={"Authorization": f"Bearer {state.token}"},
        )
        status = response.status_code
        GITHUB_API_REQUESTS_TOTAL.labels(token_index=state.index, status_code=str(status)).inc()
        state.update_from_headers(response.headers)

        if not response.is_success:
            return status, None, response.headers

        body: object = response.json()
        return status, body, response.headers

    @staticmethod
    def _build_search_query(
        *,
        min_stars: int,
        max_stars: int | None = None,
        created_after: date | None = None,
        created_before: date | None = None,
    ) -> str:
        star_clause = (
            f"stars:{min_stars}..{max_stars}" if max_stars is not None else f"stars:>={min_stars}"
        )
        parts = [star_clause]
        if created_after is not None and created_before is not None:
            parts.append(f"created:{created_after.isoformat()}..{created_before.isoformat()}")
        return " ".join(parts)

    async def _search_repositories_request(
        self,
        *,
        min_stars: int,
        max_stars: int | None,
        created_after: date | None,
        created_before: date | None,
        page: int,
        per_page: int,
    ) -> dict[str, object]:
        state = self._next_token_state()
        response = await self._http_client.get(
            _SEARCH_ENDPOINT,
            headers={"Authorization": f"Bearer {state.token}"},
            params={
                "q": self._build_search_query(
                    min_stars=min_stars,
                    max_stars=max_stars,
                    created_after=created_after,
                    created_before=created_before,
                ),
                "sort": "stars",
                "order": "desc",
                "page": page,
                "per_page": per_page,
            },
        )
        status = response.status_code
        GITHUB_API_REQUESTS_TOTAL.labels(
            token_index=state.index,
            status_code=str(status),
        ).inc()
        state.update_from_headers(response.headers)

        if status == 401:
            raise GitHubAuthenticationError()
        if status == 404:
            raise GitHubNotFoundError(resource=_SEARCH_ENDPOINT)
        if status in (403, 429):
            wait_seconds = max(0.0, state.reset_at - time.monotonic())
            raise RateLimitExceededError(reset_at_seconds=wait_seconds)
        if not response.is_success:
            raise GitHubAPIError(
                f"GitHub repository search returned {status}: {response.text[:200]}",
                status_code=status,
            )

        body: object = response.json()
        if not isinstance(body, dict):
            raise GitHubAPIError(
                "GitHub repository search returned an unexpected payload shape.",
                status_code=status,
            )
        return body

    async def get_repository_search_max_stars(self, min_stars: int) -> int:
        """Return the current highest star count among repos at or above ``min_stars``."""
        body = await self._search_repositories_request(
            min_stars=min_stars,
            max_stars=None,
            created_after=None,
            created_before=None,
            page=1,
            per_page=1,
        )
        items = body.get("items")
        if not isinstance(items, list) or not items:
            return 0
        top_item = items[0]
        if not isinstance(top_item, dict):
            return 0
        return int(top_item.get("stargazers_count") or 0)

    async def count_repositories(
        self,
        *,
        min_stars: int,
        max_stars: int,
        created_after: date,
        created_before: date,
    ) -> int:
        """Return GitHub search ``total_count`` for the provided shard."""
        body = await self._search_repositories_request(
            min_stars=min_stars,
            max_stars=max_stars,
            created_after=created_after,
            created_before=created_before,
            page=1,
            per_page=1,
        )
        return self._coerce_int(body.get("total_count"))

    async def search_repositories(
        self,
        *,
        min_stars: int,
        max_stars: int,
        created_after: date,
        created_before: date,
        page: int,
        per_page: int = _SEARCH_PAGE_SIZE,
    ) -> list[dict[str, object]]:
        """Return one search page of repositories for the provided shard."""
        body = await self._search_repositories_request(
            min_stars=min_stars,
            max_stars=max_stars,
            created_after=created_after,
            created_before=created_before,
            page=page,
            per_page=per_page,
        )
        items = body.get("items")
        if not isinstance(items, list):
            return []
        return [item for item in items if isinstance(item, dict)]

    async def fetch_repository_metadata(
        self,
        repo_full_name: str,
        *,
        rank: int | None = None,
    ) -> dict[str, object]:
        """Fetch the canonical mapped metadata for a single repository."""
        state = self._next_token_state()
        status, body, _ = await self._get_object(f"/repos/{repo_full_name}", state)
        if status == 401:
            raise GitHubAuthenticationError()
        if status == 404:
            raise GitHubNotFoundError(resource=f"/repos/{repo_full_name}")
        if status in (403, 429):
            wait_seconds = max(0.0, state.reset_at - time.monotonic())
            raise RateLimitExceededError(reset_at_seconds=wait_seconds)
        if status != 200 or not isinstance(body, dict):
            raise GitHubAPIError(
                f"GitHub repository metadata fetch returned {status} for {repo_full_name}",
                status_code=status,
            )
        mapped = map_repo_response(body, rank=rank)
        return {str(key): value for key, value in mapped.items()}

    async def _get_repo_metadata(self, repo_full_name: str) -> dict[str, object]:
        """Fetch and cache lightweight repository metadata for event filtering.

        Uses the TTL cache to avoid redundant API calls for repos seen
        frequently in the public event stream. Only the repository metadata
        document is fetched here; README and paginated issues stay out of the
        realtime ingest path because they amplify request volume sharply.
        Silently returns an empty dict on rate-limit exhaustion or API errors
        so the enrichment step never blocks the main ingestion loop.

        Args:
            repo_full_name: ``owner/name`` string, e.g. ``"torvalds/linux"``.

        Returns:
            Repository enrichment dict, or ``{}`` if unavailable.
        """
        now = time.time()
        cached = self._repo_cache.get(repo_full_name)
        if cached is not None and now < cached[1]:
            return cached[0]

        try:
            state = self._next_token_state()
        except RateLimitExceededError:
            return {}  # Enrich later; don't block the events loop

        try:
            _, body, _ = await self._get_object(f"/repos/{repo_full_name}", state)
            if not isinstance(body, dict) or not body:
                failed_lookup_ttl = 300.0  # retry after 5 min
                self._repo_cache[repo_full_name] = (
                    {"stargazers_count": 0, "_lookup_failed": True},
                    now + failed_lookup_ttl,
                )
                return {}

            bundle: dict[str, object] = {
                "metadata": body,
                "stargazers_count": int(body.get("stargazers_count") or 0),
            }
            self._repo_cache[repo_full_name] = (bundle, now + _REPO_CACHE_TTL)
            return bundle
        except (GitHubAPIError, GitHubAuthenticationError, GitHubNotFoundError):
            return {}

    async def _enrich_events_with_repo_metadata(self, events: list[dict[str, object]]) -> None:
        """Inject lightweight ``_full_repo`` metadata into each event.

        For each event, the repo's metadata document is fetched from the GitHub
        API and cached with a 1-hour TTL. Only repos whose cache entry is absent
        or expired trigger a real HTTP request. README bodies and paginated
        issues intentionally stay out of this hot path so fetch cadence stays
        bounded even when the public event stream contains many unseen repos.

        Args:
            events: List of raw GitHub event dicts to enrich in-place.
        """
        now = time.time()

        # Collect repos that need a fresh API lookup
        to_fetch: set[str] = set()
        for event in events:
            repo_info = event.get("repo") or {}
            if not isinstance(repo_info, dict):
                continue
            name = str(repo_info.get("name", ""))
            if "/" not in name:
                continue
            cached = self._repo_cache.get(name)
            if cached is None or now >= cached[1]:
                to_fetch.add(name)

        # Fetch all uncached repos concurrently (errors swallowed per-call)
        if to_fetch:
            await asyncio.gather(
                *(self._get_repo_metadata(n) for n in to_fetch),
                return_exceptions=True,
            )

        # Inject metadata into every event so the filter can make an informed
        # decision.  Events with a failed lookup get an empty dict which causes
        # the filter to reject them (fail-closed), not pass through permissively.
        now = time.time()
        for event in events:
            repo_info = event.get("repo") or {}
            if not isinstance(repo_info, dict):
                continue
            name = str(repo_info.get("name", ""))
            cached = self._repo_cache.get(name)
            if cached is not None and now < cached[1]:
                bundle = cached[0]
                if bundle.get("_lookup_failed"):
                    event["_full_repo"] = {}
                    continue
                metadata = bundle.get("metadata") or {}
                event["_full_repo"] = metadata if isinstance(metadata, dict) else {}
                event["_repo_readme_text"] = ""
                event["_repo_issues"] = []
            else:
                # Metadata fetch is still in flight or TTL expired; stay absent
                # so the filter applies permissive pass-through for this batch only.
                pass

    async def fetch_events(self) -> list[dict[str, object]]:
        """Fetch one page of public GitHub events, enriched with repo metadata.

        Applies ETag caching so repeated calls with unchanged data do not consume
        rate-limit quota.  After a successful fetch, each event is enriched with
        full repository metadata (``_full_repo``) in a concurrent, TTL-cached
        batch — allowing the star-count filter to do its job downstream.

        Returns:
            List of enriched raw event dicts, or empty list if data is unchanged (304).

        Raises:
            RateLimitExceededError: All tokens are exhausted.
            GitHubAPIError:         Non-recoverable API error.
        """
        state = self._next_token_state()
        try:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(3),
                wait=wait_exponential(multiplier=1, min=1, max=4),
                reraise=True,
            ):
                with attempt:
                    status, body, _ = await self._get(_EVENTS_ENDPOINT, state)
        except RetryError as exc:
            raise GitHubAPIError(f"GitHub API unreachable after retries: {exc}") from exc

        if status == 304 or body is None:
            logger.debug("github_client.etag_hit_no_new_events")
            return []

        logger.debug("github_client.fetched_events", count=len(body))

        # Enrich each event with full repo metadata for star-based filtering
        await self._enrich_events_with_repo_metadata(body)

        return body

    async def stream_events(self) -> AsyncGenerator[list[dict[str, object]], None]:
        """Async generator that continuously yields pages of raw GitHub events.

        Handles 304 responses transparently (yields empty list to maintain
        caller's polling cadence).  Caller is responsible for ``asyncio.sleep``
        between calls to respect rate limits.

        Yields:
            List of raw event dicts (may be empty on 304 cache hits).
        """
        while True:
            try:
                events = await self.fetch_events()
                yield events
            except RateLimitExceededError:
                raise  # Caller handles sleep + retry
            except GitHubAPIError as exc:
                logger.warning("github_client.api_error_skipping_batch", error=str(exc))
                await asyncio.sleep(5.0)
                yield []
