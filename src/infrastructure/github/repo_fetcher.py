"""GitHub repository metadata fetcher with a curated 45-field schema.

Fetches full repo metadata from ``GET /repos/{owner}/{repo}`` and maps the
response to a compact, analytics-ready dict that:

- Keeps all fields with analytic value (metrics, timestamps, classification,
  community flags, identity).
- Drops the 35 sub-resource URL templates (reconstructable from ``url``).
- Drops policy/permission fields that reflect token context, not repo state.
- Adds our own tracking fields (``fetched_at``, ``refreshed_at``, ``rank``).

The resulting dict is the canonical schema for ``data/repos/<owner>__<name>.json``.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
import time
from typing import Any

import httpx
import structlog

from src.domain.exceptions import (
    GitHubAPIError,
    GitHubAuthenticationError,
    GitHubNotFoundError,
    RateLimitExceededError,
)

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Field selection
# ---------------------------------------------------------------------------

_IDENTITY_FIELDS: tuple[str, ...] = (
    "id",
    "node_id",
    "name",
    "full_name",
    "private",
)

_URL_FIELDS: tuple[str, ...] = (
    "html_url",
    "url",
    "clone_url",
    "homepage",
)

_METRIC_FIELDS: tuple[str, ...] = (
    "stargazers_count",
    "watchers_count",
    "forks_count",
    "open_issues_count",
    "network_count",
    "subscribers_count",
    "size",
)

_TIMESTAMP_FIELDS: tuple[str, ...] = (
    "created_at",
    "updated_at",
    "pushed_at",
)

_CLASSIFICATION_FIELDS: tuple[str, ...] = (
    "language",
    "topics",
    "visibility",
    "default_branch",
    "description",
)

_FEATURE_FLAG_FIELDS: tuple[str, ...] = (
    "fork",
    "archived",
    "disabled",
    "has_issues",
    "has_wiki",
    "has_discussions",
    "has_pages",
    "allow_forking",
    "is_template",
)

# All scalar fields to copy directly from raw API response
_SCALAR_FIELDS: tuple[str, ...] = (
    _IDENTITY_FIELDS
    + _URL_FIELDS
    + _METRIC_FIELDS
    + _TIMESTAMP_FIELDS
    + _CLASSIFICATION_FIELDS
    + _FEATURE_FLAG_FIELDS
)


def _map_owner(raw_owner: dict[str, Any] | None) -> dict[str, Any] | None:
    """Extract only the useful sub-fields from the ``owner`` object."""
    if not raw_owner:
        return None
    return {
        "login": raw_owner.get("login"),
        "id": raw_owner.get("id"),
        "node_id": raw_owner.get("node_id"),
        "avatar_url": raw_owner.get("avatar_url"),
        "type": raw_owner.get("type"),
        "site_admin": raw_owner.get("site_admin"),
    }


def _map_license(raw_license: dict[str, Any] | None) -> dict[str, Any] | None:
    """Extract only the useful sub-fields from the ``license`` object."""
    if not raw_license:
        return None
    return {
        "key": raw_license.get("key"),
        "name": raw_license.get("name"),
        "spdx_id": raw_license.get("spdx_id"),
        "url": raw_license.get("url"),
    }


def map_repo_response(
    raw: dict[str, Any],
    *,
    rank: int | None = None,
    fetched_at: datetime | None = None,
) -> dict[str, Any]:
    """Map a raw GitHub Repos API response dict to the canonical 45-field schema.

    Args:
        raw: Raw JSON dict from ``GET /repos/{owner}/{repo}``.
        rank: Optional ranking position (1-based) for display ordering.
        fetched_at: Timestamp to record; defaults to ``datetime.now(UTC)``.

    Returns:
        Analytics-ready dict with exactly the curated field set.
    """
    now = fetched_at or datetime.now(UTC)

    result: dict[str, Any] = {}

    # Copy all scalar fields directly
    for field in _SCALAR_FIELDS:
        result[field] = raw.get(field)

    # Map structured sub-objects
    result["owner"] = _map_owner(raw.get("owner"))
    result["license"] = _map_license(raw.get("license"))

    # Our tracking metadata
    result["rank"] = rank
    result["fetched_at"] = now.isoformat()
    result["refreshed_at"] = now.isoformat()

    return result


_GITHUB_API_BASE = "https://api.github.com"
_HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}


async def fetch_repo(
    full_name: str,
    token: str,
    *,
    rank: int | None = None,
    timeout: float = 30.0,
) -> dict[str, Any]:
    """Fetch and map metadata for a single repository.

    Args:
        full_name: ``owner/repo`` string (e.g. ``"openai/whisper"``).
        token: GitHub personal access token (Bearer).
        rank: Optional rank to embed in the output dict.
        timeout: HTTP request timeout in seconds.

    Returns:
        Canonical 45-field dict for this repo.

    Raises:
        GitHubAuthenticationError: Token invalid or expired (401/403).
        GitHubNotFoundError: Repo not found (404).
        RateLimitExceededError: Rate limit hit (429/403 with X-RateLimit header).
        GitHubAPIError: Any other non-2xx response.
    """
    url = f"{_GITHUB_API_BASE}/repos/{full_name}"
    headers = {**_HEADERS, "Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.get(url, headers=headers)

    status = response.status_code

    if status == 200:
        raw: dict[str, Any] = response.json()
        mapped = map_repo_response(raw, rank=rank)
        logger.info(
            "repo_fetched",
            full_name=full_name,
            stars=mapped.get("stargazers_count"),
            subscribers=mapped.get("subscribers_count"),
        )
        return mapped

    if status in (401, 403):
        remaining = response.headers.get("X-RateLimit-Remaining", "?")
        if remaining == "0":
            reset_epoch = float(response.headers.get("X-RateLimit-Reset", "0") or 0.0)
            wait_seconds = max(0.0, reset_epoch - time.time())
            raise RateLimitExceededError(reset_at_seconds=wait_seconds)
        raise GitHubAuthenticationError()

    if status == 404:
        raise GitHubNotFoundError(f"Repository not found: {full_name}")

    raise GitHubAPIError(f"Unexpected HTTP {status} fetching {full_name}: {response.text[:200]}")


async def fetch_repos(
    full_names: list[str],
    token: str,
    *,
    sleep_between: float = 1.0,
) -> list[dict[str, Any]]:
    """Fetch metadata for multiple repositories sequentially.

    Args:
        full_names: List of ``owner/repo`` strings.
        token: GitHub personal access token.
        sleep_between: Seconds to sleep between API calls (rate-limit courtesy).

    Returns:
        List of canonical 45-field dicts, in the same order as ``full_names``.
        Failed fetches are logged and skipped (not raised).
    """
    results: list[dict[str, Any]] = []

    for rank, full_name in enumerate(full_names, start=1):
        try:
            repo = await fetch_repo(full_name, token, rank=rank)
            results.append(repo)
        except (GitHubAPIError, GitHubNotFoundError, RateLimitExceededError) as exc:
            logger.error("repo_fetch_failed", full_name=full_name, error=str(exc))

        if rank < len(full_names):
            await asyncio.sleep(sleep_between)

    return results
