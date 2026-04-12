"""Unit tests for RepoMetadata and RepoCategory value objects."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.domain.value_objects.repo_category import RepoCategory
from src.domain.value_objects.repo_metadata import RepoLicense, RepoMetadata, RepoOwner


def _make_metadata(**overrides: object) -> RepoMetadata:
    """Build a valid RepoMetadata instance with sensible defaults."""
    now = datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
    defaults: dict[str, object] = {
        "repo_id": 123456,
        "repo_full_name": "openai/gpt-5",
        "repo_name": "gpt-5",
        "node_id": "R_kgDOH1234",
        "private": False,
        "html_url": "https://github.com/openai/gpt-5",
        "clone_url": "https://github.com/openai/gpt-5.git",
        "homepage": "https://openai.com",
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
        "topics": ("llm", "transformer"),
        "visibility": "public",
        "default_branch": "main",
        "description": "Next generation language model",
        "category": RepoCategory.LLM,
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
            login="openai",
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
        # Arrange — two instances with the same full_name but different stars
        m1 = _make_metadata(stargazers_count=50000)
        m2 = _make_metadata(stargazers_count=60000)
        # Act + Assert
        assert m1 == m2

    def test_inequality_different_full_name(self) -> None:
        m1 = _make_metadata(repo_full_name="openai/gpt-5", repo_name="gpt-5")
        m2 = _make_metadata(repo_full_name="anthropic/claude", repo_name="claude")
        assert m1 != m2

    def test_hash_same_for_equal_objects(self) -> None:
        m1 = _make_metadata(stargazers_count=1)
        m2 = _make_metadata(stargazers_count=2)
        assert hash(m1) == hash(m2)

    def test_hash_different_for_different_full_names(self) -> None:
        m1 = _make_metadata(repo_full_name="openai/gpt-5")
        m2 = _make_metadata(repo_full_name="meta/llama", repo_name="llama")
        assert hash(m1) != hash(m2)

    def test_usable_as_dict_key(self) -> None:
        m = _make_metadata()
        d = {m: "value"}
        assert d[m] == "value"


class TestRepoMetadataImmutability:
    def test_frozen_dataclass_raises_on_setattr(self) -> None:
        m = _make_metadata()
        with pytest.raises((AttributeError, TypeError)):
            m.stargazers_count = 99999  # type: ignore[misc]

    def test_topics_is_tuple(self) -> None:
        m = _make_metadata(topics=("llm", "transformer"))
        assert isinstance(m.topics, tuple)


class TestRepoCategoryEnum:
    def test_str_returns_value(self) -> None:
        assert str(RepoCategory.LLM) == "LLM"
        assert str(RepoCategory.AGENT) == "Agent"
        assert str(RepoCategory.DATA_ENG) == "DataEng"

    def test_all_categories_defined(self) -> None:
        categories = {c.value for c in RepoCategory}
        assert "LLM" in categories
        assert "Agent" in categories
        assert "Diffusion" in categories
        assert "Multimodal" in categories
        assert "DataEng" in categories
        assert "Other" in categories
