"""SyncRepoMetadataUseCase — synchronise data/repos/*.json to ClickHouse.

Reads 45-field JSON files produced by ``repo_fetcher.py``, classifies each
repository into a category, upserts the latest state into ClickHouse, and
appends a history snapshot row for auditability.

Skips ``top5_ai_repos_summary.json`` (summary file, not a repo record).
Logs and continues on parse errors — a single bad file does not abort the run.

Usage as a script::

    python -m src.application.use_cases.sync_repo_metadata
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

import structlog

from src.domain.exceptions import RepoMetadataParseError, RepoMetadataSyncError
from src.domain.services.category_classifier import CategoryClassifier
from src.domain.value_objects.repo_metadata import RepoLicense, RepoMetadata, RepoOwner

if TYPE_CHECKING:
    from src.domain.repositories.repo_metadata_repository import RepoMetadataRepositoryABC

logger = structlog.get_logger(__name__)

# Files to skip — not individual repo records
_SKIP_FILENAMES: frozenset[str] = frozenset({"top5_ai_repos_summary.json"})

# Batch size for ClickHouse upserts
_UPSERT_BATCH_SIZE: int = 100


class SyncRepoMetadataUseCase:
    """Read JSON repo files from disk and upsert them into ClickHouse.

    This use case:
    1. Globs all ``*.json`` files in ``repo_dir``.
    2. Parses each file into a ``RepoMetadata`` value object.
    3. Classifies the repository using ``CategoryClassifier``.
    4. Calls ``repo_repo.upsert_batch()`` in batches.

    Args:
        repo_dir:   Path to the directory containing ``*.json`` repo files.
        repo_repo:  Repository port for ClickHouse persistence.
        classifier: Domain service for category classification.
    """

    def __init__(
        self,
        repo_dir: str,
        repo_repo: RepoMetadataRepositoryABC,
        classifier: CategoryClassifier,
    ) -> None:
        self._repo_dir = Path(repo_dir)
        self._repo_repo = repo_repo
        self._classifier = classifier

    async def execute(self) -> int:
        """Sync all JSON files to ClickHouse.

        Returns:
            Number of repos successfully synced.

        Raises:
            RepoMetadataSyncError: If the upsert batch fails.
        """
        json_files = sorted(self._repo_dir.glob("*.json"))
        if not json_files:
            logger.warning("sync_repo_metadata.no_files_found", path=str(self._repo_dir))
            return 0

        repos: list[RepoMetadata] = []
        parse_errors = 0

        for path in json_files:
            if path.name in _SKIP_FILENAMES:
                logger.debug("sync_repo_metadata.skipping_file", file=path.name)
                continue

            try:
                repo = self._parse_json_file(path)
                repos.append(repo)
            except RepoMetadataParseError as exc:
                parse_errors += 1
                logger.error(
                    "sync_repo_metadata.parse_error",
                    file=path.name,
                    error=str(exc),
                )

        if not repos:
            logger.warning("sync_repo_metadata.no_valid_repos", parse_errors=parse_errors)
            return 0

        # Sync latest and history in batches
        total_synced = 0
        for i in range(0, len(repos), _UPSERT_BATCH_SIZE):
            batch = repos[i : i + _UPSERT_BATCH_SIZE]
            try:
                await self._repo_repo.upsert_batch(batch)
            except Exception as exc:
                raise RepoMetadataSyncError(
                    f"Failed to upsert batch of {len(batch)} repos: {exc}"
                ) from exc

            try:
                await self._repo_repo.append_history_batch(
                    batch,
                    snapshot_source="sync_repo_metadata",
                )
            except Exception as exc:
                raise RepoMetadataSyncError(
                    f"Failed to append history batch of {len(batch)} repos: {exc}"
                ) from exc

            total_synced += len(batch)
            logger.info(
                "sync_repo_metadata.batch_synced",
                batch_size=len(batch),
                total_synced=total_synced,
            )

        logger.info(
            "sync_repo_metadata.complete",
            total_synced=total_synced,
            parse_errors=parse_errors,
        )
        return total_synced

    def _parse_json_file(self, path: Path) -> RepoMetadata:
        """Parse a single JSON file into a ``RepoMetadata`` value object.

        Args:
            path: Absolute path to the JSON file.

        Returns:
            Populated ``RepoMetadata`` instance.

        Raises:
            RepoMetadataParseError: On JSON decode error or missing required field.
        """
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RepoMetadataParseError(
                f"Cannot read/parse JSON from {path.name}: {exc}"
            ) from exc

        if not isinstance(raw, dict):
            raise RepoMetadataParseError(
                f"Repo metadata file {path.name} did not contain a JSON object."
            )

        try:
            return self._map_raw_to_domain(raw)
        except (KeyError, TypeError, ValueError) as exc:
            raise RepoMetadataParseError(
                f"Missing or invalid field in {path.name}: {exc}"
            ) from exc

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

    def _map_raw_to_domain(self, raw: dict[str, object]) -> RepoMetadata:
        """Map a raw 45-field dict (from repo_fetcher) to ``RepoMetadata``.

        Args:
            raw: Dict with the canonical 45-field schema from ``repo_fetcher.py``.

        Returns:
            ``RepoMetadata`` with all fields populated.
        """
        topics_raw = raw.get("topics")
        topics = [str(topic) for topic in topics_raw] if isinstance(topics_raw, list) else []
        description_value = raw.get("description")
        description = str(description_value) if isinstance(description_value, str) else ""
        category = self._classifier.classify(topics=topics, description=description)

        raw_owner = raw.get("owner") or {}
        if not isinstance(raw_owner, dict):
            raw_owner = {}
        owner = RepoOwner(
            login=str(raw_owner.get("login") or ""),
            owner_id=int(raw_owner.get("id") or 0),
            owner_type=str(raw_owner.get("type") or ""),
            avatar_url=str(raw_owner.get("avatar_url") or ""),
        )

        raw_license = raw.get("license") or {}
        if not isinstance(raw_license, dict):
            raw_license = {}
        license_ = RepoLicense(
            key=str(raw_license.get("key") or ""),
            name=str(raw_license.get("name") or ""),
            spdx_id=str(raw_license.get("spdx_id") or ""),
        )

        def _parse_dt(value: object) -> datetime:
            if isinstance(value, datetime):
                return value if value.tzinfo else value.replace(tzinfo=UTC)
            if isinstance(value, str) and value:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            return datetime.now(tz=UTC)

        return RepoMetadata(
            repo_id=self._coerce_int(raw.get("id")),
            repo_full_name=str(raw.get("full_name") or ""),
            repo_name=str(raw.get("name") or ""),
            node_id=str(raw.get("node_id") or ""),
            private=bool(raw.get("private", False)),
            html_url=str(raw.get("html_url") or ""),
            clone_url=str(raw.get("clone_url") or ""),
            homepage=str(raw.get("homepage") or ""),
            stargazers_count=self._coerce_int(raw.get("stargazers_count")),
            watchers_count=self._coerce_int(raw.get("watchers_count")),
            forks_count=self._coerce_int(raw.get("forks_count")),
            open_issues_count=self._coerce_int(raw.get("open_issues_count")),
            network_count=self._coerce_int(raw.get("network_count")),
            subscribers_count=self._coerce_int(raw.get("subscribers_count")),
            size_kb=self._coerce_int(raw.get("size")),
            github_created_at=_parse_dt(raw.get("created_at")),
            github_updated_at=_parse_dt(raw.get("updated_at")),
            github_pushed_at=_parse_dt(raw.get("pushed_at")),
            primary_language=str(raw.get("language") or ""),
            topics=tuple(str(t) for t in topics),
            visibility=str(raw.get("visibility") or "public"),
            default_branch=str(raw.get("default_branch") or "main"),
            description=description,
            category=category,
            is_fork=bool(raw.get("fork", False)),
            is_archived=bool(raw.get("archived", False)),
            is_disabled=bool(raw.get("disabled", False)),
            has_issues=bool(raw.get("has_issues", True)),
            has_wiki=bool(raw.get("has_wiki", False)),
            has_discussions=bool(raw.get("has_discussions", False)),
            has_pages=bool(raw.get("has_pages", False)),
            allow_forking=bool(raw.get("allow_forking", True)),
            is_template=bool(raw.get("is_template", False)),
            owner=owner,
            license=license_,
            rank=self._coerce_int(raw.get("rank")),
            fetched_at=_parse_dt(raw.get("fetched_at")),
            refreshed_at=_parse_dt(raw.get("refreshed_at")),
        )


# ── Entry point for `make sync-repos` ────────────────────────────────────────


async def _main() -> None:
    """CLI entry point: sync all JSON files to ClickHouse."""
    logging.basicConfig(level=logging.INFO)

    from src.infrastructure.config import get_settings
    from src.infrastructure.storage.clickhouse_repo_metadata_repository import (
        ClickHouseRepoMetadataRepository,
    )

    settings = get_settings()
    repository = ClickHouseRepoMetadataRepository(
        host=settings.clickhouse_host,
        port=settings.clickhouse_port,
        user=settings.clickhouse_user,
        password=settings.clickhouse_password,
        database=settings.clickhouse_database,
    )
    classifier = CategoryClassifier()
    use_case = SyncRepoMetadataUseCase(
        repo_dir=settings.repo_metadata_path,
        repo_repo=repository,
        classifier=classifier,
    )

    synced = await use_case.execute()
    logger.info("sync_complete", repos_synced=synced)


if __name__ == "__main__":
    asyncio.run(_main())
