"""Unit tests for RepoMetadata and RepoCategory value objects."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from src.domain.value_objects.repo_category import RepoCategory
from src.domain.value_objects.repo_metadata import RepoLicense, RepoMetadata, RepoOwner


def _make_metadata(**overrides: object) -> RepoMetadata:
    """Build a valid RepoMetadata instance with sensible defaults."""
    now = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)
    defaults: dict[str, object] = {
        "repo_id": 123456,
        "repo_full_name": "owner/repo",
        "repo_name": "repo",
        "node_id": "R_kgDOH1234",
        "private": False,
        "html_url": "https://github.com/owner/repo",
        "clone_url": "https://github.com/owner/repo.git",
        "homepage": "https://example.com",
        "stargazers_count": 50000,
        "watchers_count": 50000,
        "forks_count": 3000,
        "open_issues_count": 100,
        "network_count": 3050,
        "subscribers_count": 5000,
        "size_kb": 4096,
        "github_created_at": now,
        "github_updated_at": now,
        "github_pushed_at": now,
        "primary_language": "Python",
        "topics": ("analytics", "python"),
        "visibility": "public",
        "default_branch": "main",
        "description": "Repository analytics service",
        "category": RepoCategory.OTHER,
        "is_fork": False,
        "is_archived": False,
        "is_disabled": False,
        "has_issues": True,
        "has_wiki": False,
        "has_discussions": True,
        "has_pages": False,
        "allow_forking": True,
        "is_template": False,
        "owner": RepoOwner(
            login="owner",
            owner_id=14957082,
            owner_type="Organization",
            avatar_url="https://avatars.githubusercontent.com/u/14957082",
        ),
        "license": RepoLicense(key="mit", name="MIT License", spdx_id="MIT"),
        "rank": 1,
        "fetched_at": now,
        "refreshed_at": now,
    }
    defaults.update(overrides)
    return RepoMetadata(**defaults)  # type: ignore[arg-type]


class TestRepoMetadataEquality:
    def test_equality_by_repo_full_name(self) -> None:
        m1 = _make_metadata(stargazers_count=50000)
        m2 = _make_metadata(stargazers_count=60000)
        assert m1 == m2

    def test_inequality_different_full_name(self) -> None:
        m1 = _make_metadata(repo_full_name="owner/repo", repo_name="repo")
        m2 = _make_metadata(repo_full_name="other/repo", repo_name="repo")
        assert m1 != m2

    def test_hash_same_for_equal_objects(self) -> None:
        m1 = _make_metadata(stargazers_count=1)
        m2 = _make_metadata(stargazers_count=2)
        assert hash(m1) == hash(m2)

    def test_hash_different_for_different_full_names(self) -> None:
        m1 = _make_metadata(repo_full_name="owner/repo")
        m2 = _make_metadata(repo_full_name="other/repo", repo_name="repo")
        assert hash(m1) != hash(m2)

    def test_usable_as_dict_key(self) -> None:
        metadata = _make_metadata()
        lookup = {metadata: "value"}
        assert lookup[metadata] == "value"


class TestRepoMetadataImmutability:
    def test_frozen_dataclass_raises_on_setattr(self) -> None:
        metadata = _make_metadata()
        with pytest.raises((AttributeError, TypeError)):
            metadata.stargazers_count = 99999  # type: ignore[misc]

    def test_topics_is_tuple(self) -> None:
        metadata = _make_metadata(topics=("analytics", "python"))
        assert isinstance(metadata.topics, tuple)


class TestRepoCategoryEnum:
    def test_str_returns_value(self) -> None:
        assert str(RepoCategory.OTHER) == "Other"

    def test_all_categories_defined(self) -> None:
        assert {category.value for category in RepoCategory} == {"Other"}
