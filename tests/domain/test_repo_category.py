"""Unit tests for the RepoCategory value object."""

from __future__ import annotations

import pytest

from src.domain.value_objects.repo_category import RepoCategory


class TestRepoCategoryEnum:
    """Tests for RepoCategory enumeration members."""

    def test_only_neutral_category_exists(self) -> None:
        assert {category.value for category in RepoCategory} == {"Other"}

    def test_other_category_value(self) -> None:
        assert RepoCategory.OTHER.value == "Other"


class TestRepoCategoryStrBehaviour:
    def test_str_returns_value(self) -> None:
        assert str(RepoCategory.OTHER) == "Other"

    def test_is_str_subclass(self) -> None:
        assert isinstance(RepoCategory.OTHER, str)


class TestRepoCategoryComparison:
    def test_category_equal_to_its_string_value(self) -> None:
        assert RepoCategory.OTHER == "Other"

    @pytest.mark.parametrize("category", list(RepoCategory))
    def test_category_is_hashable(self, category: RepoCategory) -> None:
        category_set = {category}
        assert category in category_set
