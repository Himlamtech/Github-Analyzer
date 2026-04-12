"""Repo-first catalog discovery for star-threshold coverage.

This use case builds a durable repository seed list using GitHub repository
search instead of relying on the public events stream. Search queries are
sharded recursively by star range and, when necessary, repository creation
date so each shard stays under GitHub's search pagination limits.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
import json
import math
from pathlib import Path
from typing import Protocol

import structlog

from src.domain.exceptions import ValidationError

logger = structlog.get_logger(__name__)

JsonObject = dict[str, object]
_SEARCH_PAGE_SIZE = 100
_METADATA_FETCH_BATCH_SIZE = 10


@dataclass(frozen=True)
class RepoCatalogShard:
    """One GitHub repository search shard."""

    min_stars: int
    max_stars: int
    created_after: date
    created_before: date

    def to_dict(self, *, matched_count: int) -> JsonObject:
        return {
            "min_stars": self.min_stars,
            "max_stars": self.max_stars,
            "created_after": self.created_after.isoformat(),
            "created_before": self.created_before.isoformat(),
            "matched_count": matched_count,
        }

    def label(self) -> str:
        return (
            f"stars:{self.min_stars}..{self.max_stars} "
            f"created:{self.created_after.isoformat()}..{self.created_before.isoformat()}"
        )


@dataclass(frozen=True)
class RepoCatalogShardResult:
    """A leaf search shard with its GitHub ``total_count``."""

    shard: RepoCatalogShard
    matched_count: int


class RepoCatalogClientProtocol(Protocol):
    """Protocol required by ``DiscoverRepoCatalogUseCase``."""

    async def get_repository_search_max_stars(self, min_stars: int) -> int: ...

    async def count_repositories(
        self,
        *,
        min_stars: int,
        max_stars: int,
        created_after: date,
        created_before: date,
    ) -> int: ...

    async def search_repositories(
        self,
        *,
        min_stars: int,
        max_stars: int,
        created_after: date,
        created_before: date,
        page: int,
        per_page: int = _SEARCH_PAGE_SIZE,
    ) -> list[dict[str, object]]: ...

    async def fetch_repository_metadata(
        self,
        repo_full_name: str,
        *,
        rank: int | None = None,
    ) -> dict[str, object]: ...


class DiscoverRepoCatalogUseCase:
    """Build a durable repository catalog from GitHub Search."""

    def __init__(
        self,
        discovery_client: RepoCatalogClientProtocol,
        *,
        repo_catalog_dir: str,
        repo_metadata_dir: str,
        min_stars: int,
        max_shard_size: int,
        start_date: date,
        today: date | None = None,
    ) -> None:
        self._client = discovery_client
        self._repo_catalog_dir = Path(repo_catalog_dir)
        self._repo_metadata_dir = Path(repo_metadata_dir)
        self._min_stars = min_stars
        self._max_shard_size = max_shard_size
        self._start_date = start_date
        self._today = today or datetime.now(tz=UTC).date()

    async def execute(self, limit: int | None = None) -> int:
        """Discover repositories and persist the catalog snapshot plus repo JSON files."""
        max_stars = await self._client.get_repository_search_max_stars(self._min_stars)
        if max_stars < self._min_stars:
            logger.warning(
                "discover_repo_catalog.no_repositories_found",
                min_stars=self._min_stars,
            )
            return 0

        root_shard = RepoCatalogShard(
            min_stars=self._min_stars,
            max_stars=max_stars,
            created_after=self._start_date,
            created_before=self._today,
        )
        shard_results = await self._collect_shards(root_shard)
        repo_candidates = await self._collect_repo_candidates(shard_results)
        sorted_candidates = self._sort_candidates(repo_candidates)
        if limit is not None:
            sorted_candidates = sorted_candidates[:limit]

        full_repo_metadata = await self._fetch_full_repo_metadata(sorted_candidates)
        self._write_outputs(
            shard_results=shard_results,
            repo_candidates=sorted_candidates,
            full_repos=full_repo_metadata,
        )

        logger.info(
            "discover_repo_catalog.complete",
            shard_count=len(shard_results),
            repo_count=len(full_repo_metadata),
            min_stars=self._min_stars,
        )
        return len(full_repo_metadata)

    async def _collect_shards(self, shard: RepoCatalogShard) -> list[RepoCatalogShardResult]:
        matched_count = await self._client.count_repositories(
            min_stars=shard.min_stars,
            max_stars=shard.max_stars,
            created_after=shard.created_after,
            created_before=shard.created_before,
        )
        if matched_count == 0:
            return []
        if matched_count <= self._max_shard_size:
            return [RepoCatalogShardResult(shard=shard, matched_count=matched_count)]

        logger.info(
            "discover_repo_catalog.split_shard",
            shard=shard.label(),
            matched_count=matched_count,
        )

        star_split = self._split_star_shard(shard)
        if star_split is not None:
            left, right = star_split
            left_results = await self._collect_shards(left)
            right_results = await self._collect_shards(right)
            return [*left_results, *right_results]

        date_split = self._split_date_shard(shard)
        if date_split is not None:
            left, right = date_split
            left_results = await self._collect_shards(left)
            right_results = await self._collect_shards(right)
            return [*left_results, *right_results]

        raise ValidationError(
            f"Search shard cannot be split further while still exceeding limit: {shard.label()}"
        )

    @staticmethod
    def _split_star_shard(
        shard: RepoCatalogShard,
    ) -> tuple[RepoCatalogShard, RepoCatalogShard] | None:
        if shard.min_stars >= shard.max_stars:
            return None
        midpoint = (shard.min_stars + shard.max_stars) // 2
        if midpoint < shard.min_stars or midpoint >= shard.max_stars:
            return None
        return (
            RepoCatalogShard(
                min_stars=shard.min_stars,
                max_stars=midpoint,
                created_after=shard.created_after,
                created_before=shard.created_before,
            ),
            RepoCatalogShard(
                min_stars=midpoint + 1,
                max_stars=shard.max_stars,
                created_after=shard.created_after,
                created_before=shard.created_before,
            ),
        )

    @staticmethod
    def _split_date_shard(
        shard: RepoCatalogShard,
    ) -> tuple[RepoCatalogShard, RepoCatalogShard] | None:
        if shard.created_after >= shard.created_before:
            return None
        span_days = (shard.created_before - shard.created_after).days
        if span_days <= 0:
            return None
        midpoint = shard.created_after + timedelta(days=span_days // 2)
        if midpoint < shard.created_after or midpoint >= shard.created_before:
            return None
        return (
            RepoCatalogShard(
                min_stars=shard.min_stars,
                max_stars=shard.max_stars,
                created_after=shard.created_after,
                created_before=midpoint,
            ),
            RepoCatalogShard(
                min_stars=shard.min_stars,
                max_stars=shard.max_stars,
                created_after=midpoint + timedelta(days=1),
                created_before=shard.created_before,
            ),
        )

    async def _collect_repo_candidates(
        self,
        shard_results: list[RepoCatalogShardResult],
    ) -> dict[str, JsonObject]:
        repo_candidates: dict[str, JsonObject] = {}

        for shard_result in shard_results:
            page_count = math.ceil(shard_result.matched_count / _SEARCH_PAGE_SIZE)
            for page in range(1, page_count + 1):
                items = await self._client.search_repositories(
                    min_stars=shard_result.shard.min_stars,
                    max_stars=shard_result.shard.max_stars,
                    created_after=shard_result.shard.created_after,
                    created_before=shard_result.shard.created_before,
                    page=page,
                    per_page=_SEARCH_PAGE_SIZE,
                )
                for item in items:
                    repo_full_name = str(item.get("full_name") or "")
                    if not repo_full_name:
                        continue
                    source_shards = repo_candidates.get(repo_full_name, {}).get("source_shards")
                    if not isinstance(source_shards, list):
                        source_shards = []
                    if shard_result.shard.label() not in source_shards:
                        source_shards.append(shard_result.shard.label())
                    repo_candidates[repo_full_name] = {
                        "full_name": repo_full_name,
                        "html_url": str(item.get("html_url") or ""),
                        "stargazers_count": self._coerce_int(item.get("stargazers_count")),
                        "source_shards": source_shards,
                    }
        return repo_candidates

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

    @staticmethod
    def _sort_candidates(repo_candidates: dict[str, JsonObject]) -> list[JsonObject]:
        return sorted(
            repo_candidates.values(),
            key=lambda candidate: (
                -DiscoverRepoCatalogUseCase._coerce_int(candidate.get("stargazers_count")),
                str(candidate.get("full_name") or ""),
            ),
        )

    async def _fetch_full_repo_metadata(
        self,
        repo_candidates: list[JsonObject],
    ) -> list[JsonObject]:
        full_repos: list[JsonObject] = []
        for start in range(0, len(repo_candidates), _METADATA_FETCH_BATCH_SIZE):
            batch = repo_candidates[start : start + _METADATA_FETCH_BATCH_SIZE]
            tasks = [
                self._client.fetch_repository_metadata(
                    str(candidate.get("full_name") or ""),
                    rank=start + index + 1,
                )
                for index, candidate in enumerate(batch)
                if candidate.get("full_name")
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, BaseException):
                    logger.warning("discover_repo_catalog.repo_fetch_failed", error=str(result))
                    continue
                full_repos.append(result)
        return full_repos

    def _write_outputs(
        self,
        *,
        shard_results: list[RepoCatalogShardResult],
        repo_candidates: list[JsonObject],
        full_repos: list[JsonObject],
    ) -> None:
        self._repo_catalog_dir.mkdir(parents=True, exist_ok=True)
        self._repo_metadata_dir.mkdir(parents=True, exist_ok=True)

        generated_at = datetime.now(tz=UTC)
        timestamp = generated_at.strftime("%Y%m%dT%H%M%SZ")

        for repo in full_repos:
            repo_full_name = str(repo.get("full_name") or "")
            if not repo_full_name:
                continue
            file_path = self._repo_metadata_dir / self._repo_filename(repo_full_name)
            file_path.write_text(
                json.dumps(repo, ensure_ascii=True, indent=2, sort_keys=True),
                encoding="utf-8",
            )

        snapshot: JsonObject = {
            "generated_at": generated_at.isoformat(),
            "min_stars": self._min_stars,
            "max_shard_size": self._max_shard_size,
            "repo_count": len(full_repos),
            "shards": [
                result.shard.to_dict(matched_count=result.matched_count)
                for result in shard_results
            ],
            "repos": repo_candidates,
        }
        latest_path = self._repo_catalog_dir / "latest.json"
        timestamped_path = self._repo_catalog_dir / f"repo_catalog_{timestamp}.json"
        payload = json.dumps(snapshot, ensure_ascii=True, indent=2, sort_keys=True)
        latest_path.write_text(payload, encoding="utf-8")
        timestamped_path.write_text(payload, encoding="utf-8")

    @staticmethod
    def _repo_filename(repo_full_name: str) -> str:
        owner, repo = repo_full_name.split("/", maxsplit=1)
        return f"{owner}__{repo}.json"


async def _main() -> None:
    """CLI entry point for repo-first catalog discovery."""
    from src.infrastructure.config import get_settings
    from src.infrastructure.github.client import GitHubClient

    settings = get_settings()

    async with GitHubClient(
        tokens=settings.github_tokens_list,
        base_url=str(settings.github_api_base_url),
    ) as client:
        use_case = DiscoverRepoCatalogUseCase(
            discovery_client=client,
            repo_catalog_dir=settings.repo_catalog_path,
            repo_metadata_dir=settings.repo_metadata_path,
            min_stars=settings.repo_discovery_min_stars,
            max_shard_size=settings.repo_discovery_max_shard_size,
            start_date=settings.repo_discovery_start_date,
        )
        discovered = await use_case.execute()
        logger.info("discover_repo_catalog.done", discovered=discovered)


if __name__ == "__main__":
    asyncio.run(_main())
