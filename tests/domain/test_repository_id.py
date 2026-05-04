"""Unit tests for the RepositoryId value object."""

from __future__ import annotations

import pytest

from src.domain.exceptions import InvalidRepositoryIdError
from src.domain.value_objects.repository_id import RepositoryId


class TestRepositoryIdCreation:
    """Tests for valid and invalid RepositoryId construction."""

    def test_create_valid_repository_id_succeeds(self) -> None:
        """Happy path: valid repo_id and repo_name produce a RepositoryId."""
        repo_id = RepositoryId.from_api(repo_id=12345, repo_name="owner/repo")
        assert repo_id.value == 12345
        assert repo_id.name == "owner/repo"

    def test_zero_repo_id_raises_invalid_repository_id_error(self) -> None:
        """Edge case: repo_id of 0 must raise InvalidRepositoryIdError."""
        with pytest.raises(InvalidRepositoryIdError):
            RepositoryId.from_api(repo_id=0, repo_name="owner/repo")

    def test_negative_repo_id_raises_invalid_repository_id_error(self) -> None:
        """Edge case: negative repo_id must raise InvalidRepositoryIdError."""
        with pytest.raises(InvalidRepositoryIdError):
            RepositoryId.from_api(repo_id=-1, repo_name="owner/repo")

    def test_name_without_slash_raises_invalid_repository_id_error(self) -> None:
        """Edge case: name without '/' separator must raise InvalidRepositoryIdError."""
        with pytest.raises(InvalidRepositoryIdError):
            RepositoryId.from_api(repo_id=1, repo_name="noslash")

    def test_empty_name_raises_invalid_repository_id_error(self) -> None:
        """Edge case: empty name must raise InvalidRepositoryIdError."""
        with pytest.raises(InvalidRepositoryIdError):
            RepositoryId.from_api(repo_id=1, repo_name="")

    def test_exceeding_max_repo_id_raises_invalid_repository_id_error(self) -> None:
        """Edge case: repo_id exceeding 10^12 must raise InvalidRepositoryIdError."""
        with pytest.raises(InvalidRepositoryIdError):
            RepositoryId.from_api(repo_id=10**12 + 1, repo_name="owner/repo")

    def test_max_valid_repo_id_succeeds(self) -> None:
        """Boundary: repo_id equal to 10^12 must still be accepted."""
        repo_id = RepositoryId.from_api(repo_id=10**12, repo_name="owner/repo")
        assert repo_id.value == 10**12
        assert repo_id.name == "owner/repo"


class TestRepositoryIdProperties:
    """Tests for owner and repo property accessors."""

    def test_owner_property_returns_correct_value(self) -> None:
        """owner property must return the portion before the slash."""
        repo_id = RepositoryId.from_api(repo_id=1, repo_name="openai/gpt-4")
        assert repo_id.owner == "openai"

    def test_repo_property_returns_correct_value(self) -> None:
        """repo property must return the portion after the slash."""
        repo_id = RepositoryId.from_api(repo_id=1, repo_name="openai/gpt-4")
        assert repo_id.repo == "gpt-4"

    def test_owner_with_org_name_containing_hyphens(self) -> None:
        """owner property works correctly when org name contains hyphens."""
        repo_id = RepositoryId.from_api(repo_id=1, repo_name="hugging-face/transformers")
        assert repo_id.owner == "hugging-face"

    def test_str_representation_returns_full_name(self) -> None:
        """__str__ must return the owner/repo string."""
        repo_id = RepositoryId.from_api(repo_id=999, repo_name="torvalds/linux")
        assert str(repo_id) == "torvalds/linux"


class TestRepositoryIdEquality:
    """Tests for frozen dataclass equality and hashability."""

    def test_same_values_are_equal(self) -> None:
        """Two RepositoryIds with identical value and name must be equal."""
        r1 = RepositoryId.from_api(repo_id=42, repo_name="owner/repo")
        r2 = RepositoryId.from_api(repo_id=42, repo_name="owner/repo")
        assert r1 == r2

    def test_different_values_are_not_equal(self) -> None:
        """Two RepositoryIds with different values must not be equal."""
        r1 = RepositoryId.from_api(repo_id=1, repo_name="owner/repo")
        r2 = RepositoryId.from_api(repo_id=2, repo_name="owner/repo")
        assert r1 != r2

    def test_repository_id_is_hashable(self) -> None:
        """RepositoryId must be usable as a dict key or set member."""
        r = RepositoryId.from_api(repo_id=1, repo_name="owner/repo")
        repo_set = {r}
        assert r in repo_set

    def test_repository_id_is_immutable(self) -> None:
        """Frozen dataclass must raise FrozenInstanceError on attribute write."""
        from dataclasses import FrozenInstanceError

        r = RepositoryId.from_api(repo_id=1, repo_name="owner/repo")
        with pytest.raises(FrozenInstanceError):
            r.value = 999  # type: ignore[misc]
