"""Unit tests for SyncRepoMetadataUseCase.

All I/O is mocked — no real filesystem access or ClickHouse connections.
JSON parsing is tested via temporary files created with ``tmp_path`` fixtures.
"""

from __future__ import annotations

from datetime import UTC, datetime
import json
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock

import pytest

from src.application.use_cases.sync_repo_metadata import SyncRepoMetadataUseCase
from src.domain.exceptions import RepoMetadataSyncError
from src.domain.services.category_classifier import CategoryClassifier
from src.domain.value_objects.repo_category import RepoCategory

if TYPE_CHECKING:
    from pathlib import Path

    from src.domain.value_objects.repo_metadata import RepoMetadata


# ── Helpers ───────────────────────────────────────────────────────────────────

_NOW_STR = "2024-06-15T12:00:00Z"
_NOW = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)


def _repo_json(
    full_name: str = "openai/gpt-5",
    topics: list[str] | None = None,
    **overrides: object,
) -> dict[str, object]:
    """Build a minimal valid repo JSON dict mirroring ``repo_fetcher`` output."""
    base: dict[str, object] = {
        "id": 123456,
        "full_name": full_name,
        "name": full_name.split("/")[-1],
        "node_id": "R_kgDOH1234",
        "private": False,
        "html_url": f"https://github.com/{full_name}",
        "clone_url": f"https://github.com/{full_name}.git",
        "homepage": "",
        "stargazers_count": 50000,
        "watchers_count": 50000,
        "forks_count": 3000,
        "open_issues_count": 100,
        "network_count": 3050,
        "subscribers_count": 5000,
        "size": 4096,
        "created_at": _NOW_STR,
        "updated_at": _NOW_STR,
        "pushed_at": _NOW_STR,
        "language": "Python",
        "topics": topics if topics is not None else ["llm", "transformer"],
        "visibility": "public",
        "default_branch": "main",
        "description": "Next generation language model",
        "fork": False,
        "archived": False,
        "disabled": False,
        "has_issues": True,
        "has_wiki": False,
        "has_discussions": True,
        "has_pages": False,
        "allow_forking": True,
        "is_template": False,
        "owner": {
            "login": full_name.split("/")[0],
            "id": 14957082,
            "type": "Organization",
            "avatar_url": "https://avatars.githubusercontent.com/u/14957082",
        },
        "license": {"key": "mit", "name": "MIT License", "spdx_id": "MIT"},
        "rank": 1,
        "fetched_at": _NOW_STR,
        "refreshed_at": _NOW_STR,
    }
    base.update(overrides)
    return base


def _write_repo_file(path: Path, data: dict[str, object]) -> None:
    path.write_text(json.dumps(data), encoding="utf-8")


def _make_use_case(
    repo_dir: str,
    repo_repo: AsyncMock,
    classifier: CategoryClassifier | None = None,
) -> SyncRepoMetadataUseCase:
    return SyncRepoMetadataUseCase(
        repo_dir=repo_dir,
        repo_repo=repo_repo,
        classifier=classifier or CategoryClassifier(),
    )


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_repo() -> AsyncMock:
    """Mock ``RepoMetadataRepositoryABC`` with a no-op ``upsert_batch``."""
    repo = AsyncMock()
    repo.upsert_batch = AsyncMock(return_value=None)
    repo.append_history_batch = AsyncMock(return_value=None)
    return repo


# ── Happy path ────────────────────────────────────────────────────────────────


class TestSyncRepoMetadataUseCaseHappyPath:
    async def test_execute_returns_count_of_synced_repos(
        self,
        tmp_path: Path,
        mock_repo: AsyncMock,
    ) -> None:
        """Single valid JSON file → execute() returns 1."""
        _write_repo_file(tmp_path / "openai_gpt5.json", _repo_json())
        uc = _make_use_case(str(tmp_path), mock_repo)

        result = await uc.execute()

        assert result == 1

    async def test_execute_calls_upsert_batch_once_for_small_set(
        self,
        tmp_path: Path,
        mock_repo: AsyncMock,
    ) -> None:
        """3 files → upsert_batch called once (below UPSERT_BATCH_SIZE=100)."""
        for i in range(3):
            _write_repo_file(
                tmp_path / f"repo_{i}.json",
                _repo_json(full_name=f"org/repo-{i}"),
            )
        uc = _make_use_case(str(tmp_path), mock_repo)

        await uc.execute()

        mock_repo.upsert_batch.assert_called_once()
        mock_repo.append_history_batch.assert_called_once()

    async def test_execute_passes_correct_repo_metadata_to_upsert(
        self,
        tmp_path: Path,
        mock_repo: AsyncMock,
    ) -> None:
        """Parsed ``RepoMetadata`` must carry the correct ``repo_full_name``."""
        _write_repo_file(tmp_path / "repo.json", _repo_json(full_name="anthropic/claude"))
        uc = _make_use_case(str(tmp_path), mock_repo)

        await uc.execute()

        call_args = mock_repo.upsert_batch.call_args
        batch: list[RepoMetadata] = call_args[0][0]
        assert len(batch) == 1
        assert batch[0].repo_full_name == "anthropic/claude"

    async def test_execute_classifies_llm_topics_correctly(
        self,
        tmp_path: Path,
        mock_repo: AsyncMock,
    ) -> None:
        """Topics containing 'llm' should be classified as RepoCategory.LLM."""
        _write_repo_file(
            tmp_path / "repo.json",
            _repo_json(full_name="openai/gpt-5", topics=["llm", "transformer"]),
        )
        uc = _make_use_case(str(tmp_path), mock_repo)

        await uc.execute()

        batch: list[RepoMetadata] = mock_repo.upsert_batch.call_args[0][0]
        assert batch[0].category == RepoCategory.LLM

    async def test_execute_syncs_multiple_repos_returns_total(
        self,
        tmp_path: Path,
        mock_repo: AsyncMock,
    ) -> None:
        """10 valid files → execute() returns 10."""
        for i in range(10):
            _write_repo_file(
                tmp_path / f"repo_{i}.json",
                _repo_json(full_name=f"org/repo-{i}"),
            )
        uc = _make_use_case(str(tmp_path), mock_repo)

        result = await uc.execute()

        assert result == 10

    async def test_execute_appends_history_with_sync_source(
        self,
        tmp_path: Path,
        mock_repo: AsyncMock,
    ) -> None:
        """Each sync batch must also append an audit snapshot into history."""
        _write_repo_file(tmp_path / "repo.json", _repo_json(full_name="org/repo"))
        uc = _make_use_case(str(tmp_path), mock_repo)

        await uc.execute()

        call_args = mock_repo.append_history_batch.call_args
        assert call_args.kwargs["snapshot_source"] == "sync_repo_metadata"
        batch: list[RepoMetadata] = call_args.args[0]
        assert batch[0].repo_full_name == "org/repo"

    async def test_execute_batches_large_set(
        self,
        tmp_path: Path,
        mock_repo: AsyncMock,
    ) -> None:
        """120 files → upsert_batch called twice (batches of 100)."""
        for i in range(120):
            _write_repo_file(
                tmp_path / f"repo_{i:03d}.json",
                _repo_json(full_name=f"org/repo-{i}"),
            )
        uc = _make_use_case(str(tmp_path), mock_repo)

        await uc.execute()

        assert mock_repo.upsert_batch.call_count == 2


# ── Skip logic ────────────────────────────────────────────────────────────────


class TestSyncRepoMetadataUseCaseSkipFiles:
    async def test_execute_skips_top5_summary_file(
        self,
        tmp_path: Path,
        mock_repo: AsyncMock,
    ) -> None:
        """``top5_ai_repos_summary.json`` must never be parsed."""
        _write_repo_file(
            tmp_path / "top5_ai_repos_summary.json",
            {"not": "a repo"},
        )
        _write_repo_file(tmp_path / "real_repo.json", _repo_json())
        uc = _make_use_case(str(tmp_path), mock_repo)

        result = await uc.execute()

        assert result == 1
        batch: list[RepoMetadata] = mock_repo.upsert_batch.call_args[0][0]
        assert all(r.repo_full_name != "" for r in batch)

    async def test_execute_returns_zero_when_only_summary_file(
        self,
        tmp_path: Path,
        mock_repo: AsyncMock,
    ) -> None:
        """Directory containing only the summary file → returns 0, no upsert."""
        _write_repo_file(
            tmp_path / "top5_ai_repos_summary.json",
            {"not": "a repo"},
        )
        uc = _make_use_case(str(tmp_path), mock_repo)

        result = await uc.execute()

        assert result == 0
        mock_repo.upsert_batch.assert_not_called()
        mock_repo.append_history_batch.assert_not_called()

    async def test_execute_returns_zero_for_empty_directory(
        self,
        tmp_path: Path,
        mock_repo: AsyncMock,
    ) -> None:
        """Empty directory → returns 0 without calling upsert."""
        uc = _make_use_case(str(tmp_path), mock_repo)

        result = await uc.execute()

        assert result == 0
        mock_repo.upsert_batch.assert_not_called()


# ── Error paths ───────────────────────────────────────────────────────────────


class TestSyncRepoMetadataUseCaseErrorHandling:
    async def test_execute_continues_past_bad_json_file(
        self,
        tmp_path: Path,
        mock_repo: AsyncMock,
    ) -> None:
        """A malformed JSON file must be logged and skipped; valid files still sync."""
        (tmp_path / "bad.json").write_text("{not valid json", encoding="utf-8")
        _write_repo_file(tmp_path / "good.json", _repo_json(full_name="org/valid-repo"))
        uc = _make_use_case(str(tmp_path), mock_repo)

        result = await uc.execute()

        assert result == 1
        batch: list[RepoMetadata] = mock_repo.upsert_batch.call_args[0][0]
        assert batch[0].repo_full_name == "org/valid-repo"

    async def test_execute_continues_past_missing_required_field(
        self,
        tmp_path: Path,
        mock_repo: AsyncMock,
    ) -> None:
        """JSON with a field that causes a TypeError on coercion must be skipped."""
        # owner.id is coerced with int() — a non-numeric string triggers ValueError
        bad_data = _repo_json(full_name="org/bad-owner")
        bad_data["owner"] = {"login": "org", "id": "not-an-int", "type": "Org", "avatar_url": ""}
        _write_repo_file(tmp_path / "bad_owner.json", bad_data)
        _write_repo_file(tmp_path / "complete.json", _repo_json(full_name="org/complete"))
        uc = _make_use_case(str(tmp_path), mock_repo)

        # Should not raise — bad_owner.json is skipped
        result = await uc.execute()

        # complete.json is still synced
        assert result == 1

    async def test_execute_raises_sync_error_on_upsert_failure(
        self,
        tmp_path: Path,
        mock_repo: AsyncMock,
    ) -> None:
        """If ``upsert_batch`` raises, a ``RepoMetadataSyncError`` must propagate."""
        _write_repo_file(tmp_path / "repo.json", _repo_json())
        mock_repo.upsert_batch.side_effect = RuntimeError("ClickHouse unavailable")
        uc = _make_use_case(str(tmp_path), mock_repo)

        with pytest.raises(RepoMetadataSyncError, match="Failed to upsert batch"):
            await uc.execute()

    async def test_execute_raises_sync_error_on_history_append_failure(
        self,
        tmp_path: Path,
        mock_repo: AsyncMock,
    ) -> None:
        """If history append fails, the sync must still surface a failure."""
        _write_repo_file(tmp_path / "repo.json", _repo_json())
        mock_repo.append_history_batch.side_effect = RuntimeError("history unavailable")
        uc = _make_use_case(str(tmp_path), mock_repo)

        with pytest.raises(RepoMetadataSyncError, match="Failed to append history batch"):
            await uc.execute()

    async def test_execute_all_bad_files_returns_zero(
        self,
        tmp_path: Path,
        mock_repo: AsyncMock,
    ) -> None:
        """If every file fails to parse, returns 0 without calling upsert."""
        for i in range(3):
            (tmp_path / f"bad_{i}.json").write_text("{{invalid}}", encoding="utf-8")
        uc = _make_use_case(str(tmp_path), mock_repo)

        result = await uc.execute()

        assert result == 0
        mock_repo.upsert_batch.assert_not_called()
        mock_repo.append_history_batch.assert_not_called()


# ── Field mapping ─────────────────────────────────────────────────────────────


class TestSyncRepoMetadataFieldMapping:
    async def test_execute_maps_all_numeric_counts(
        self,
        tmp_path: Path,
        mock_repo: AsyncMock,
    ) -> None:
        """Numeric fields (stars, forks, etc.) must be mapped correctly."""
        data = _repo_json(
            stargazers_count=99999,
            forks_count=5555,
            open_issues_count=42,
        )
        _write_repo_file(tmp_path / "repo.json", data)
        uc = _make_use_case(str(tmp_path), mock_repo)

        await uc.execute()

        batch: list[RepoMetadata] = mock_repo.upsert_batch.call_args[0][0]
        repo = batch[0]
        assert repo.stargazers_count == 99999
        assert repo.forks_count == 5555
        assert repo.open_issues_count == 42

    async def test_execute_maps_topics_as_tuple(
        self,
        tmp_path: Path,
        mock_repo: AsyncMock,
    ) -> None:
        """Topics from JSON list must be stored as a tuple in the value object."""
        _write_repo_file(
            tmp_path / "repo.json",
            _repo_json(topics=["llm", "rag", "agent"]),
        )
        uc = _make_use_case(str(tmp_path), mock_repo)

        await uc.execute()

        batch: list[RepoMetadata] = mock_repo.upsert_batch.call_args[0][0]
        assert isinstance(batch[0].topics, tuple)
        assert set(batch[0].topics) == {"llm", "rag", "agent"}

    async def test_execute_maps_datetime_fields(
        self,
        tmp_path: Path,
        mock_repo: AsyncMock,
    ) -> None:
        """ISO-8601 datetime strings must be parsed into timezone-aware datetimes."""
        _write_repo_file(tmp_path / "repo.json", _repo_json())
        uc = _make_use_case(str(tmp_path), mock_repo)

        await uc.execute()

        batch: list[RepoMetadata] = mock_repo.upsert_batch.call_args[0][0]
        repo = batch[0]
        assert repo.github_created_at.tzinfo is not None
        assert repo.github_pushed_at.tzinfo is not None
        assert repo.github_created_at == _NOW

    async def test_execute_maps_owner_fields(
        self,
        tmp_path: Path,
        mock_repo: AsyncMock,
    ) -> None:
        """Owner login and type must be mapped into ``RepoOwner`` sub-object."""
        _write_repo_file(tmp_path / "repo.json", _repo_json(full_name="anthropic/claude"))
        uc = _make_use_case(str(tmp_path), mock_repo)

        await uc.execute()

        batch: list[RepoMetadata] = mock_repo.upsert_batch.call_args[0][0]
        assert batch[0].owner.login == "anthropic"
        assert batch[0].owner.owner_type == "Organization"

    async def test_execute_maps_none_topics_to_empty_tuple(
        self,
        tmp_path: Path,
        mock_repo: AsyncMock,
    ) -> None:
        """Missing topics field must not raise — results in an empty tuple."""
        data = _repo_json()
        data["topics"] = None  # type: ignore[assignment]
        _write_repo_file(tmp_path / "repo.json", data)
        uc = _make_use_case(str(tmp_path), mock_repo)

        result = await uc.execute()

        assert result == 1
        batch: list[RepoMetadata] = mock_repo.upsert_batch.call_args[0][0]
        assert batch[0].topics == ()
