"""Unit tests for the RepoCategory value object."""

from __future__ import annotations

import pytest

from src.domain.value_objects.repo_category import RepoCategory


class TestRepoCategoryEnum:
    """Tests for RepoCategory enumeration members."""

    def test_all_expected_categories_exist(self) -> None:
        """All six categories must be defined."""
        expected = {"LLM", "Agent", "Diffusion", "Multimodal", "DataEng", "Other"}
        actual = {c.value for c in RepoCategory}
        assert expected == actual

    def test_llm_category_value(self) -> None:
        """RepoCategory.LLM must have value 'LLM'."""
        assert RepoCategory.LLM.value == "LLM"

    def test_agent_category_value(self) -> None:
        """RepoCategory.AGENT must have value 'Agent'."""
        assert RepoCategory.AGENT.value == "Agent"

    def test_diffusion_category_value(self) -> None:
        """RepoCategory.DIFFUSION must have value 'Diffusion'."""
        assert RepoCategory.DIFFUSION.value == "Diffusion"

    def test_multimodal_category_value(self) -> None:
        """RepoCategory.MULTIMODAL must have value 'Multimodal'."""
        assert RepoCategory.MULTIMODAL.value == "Multimodal"

    def test_data_eng_category_value(self) -> None:
        """RepoCategory.DATA_ENG must have value 'DataEng'."""
        assert RepoCategory.DATA_ENG.value == "DataEng"

    def test_other_category_value(self) -> None:
        """RepoCategory.OTHER must have value 'Other'."""
        assert RepoCategory.OTHER.value == "Other"


class TestRepoCategoryStrBehaviour:
    """Tests for str-subclass serialisation behaviour."""

    def test_str_returns_value(self) -> None:
        """__str__ must return the raw string value without enum wrapping."""
        assert str(RepoCategory.LLM) == "LLM"

    def test_is_str_subclass(self) -> None:
        """RepoCategory must be directly usable as a str in JSON contexts."""
        assert isinstance(RepoCategory.LLM, str)

    def test_all_categories_str_equal_their_value(self) -> None:
        """Every category's str representation must equal its value."""
        for category in RepoCategory:
            assert str(category) == category.value


class TestRepoCategoryComparison:
    """Tests for equality semantics."""

    def test_same_category_is_equal(self) -> None:
        """Two references to the same category must be equal."""
        assert RepoCategory.LLM == RepoCategory.LLM

    def test_different_categories_are_not_equal(self) -> None:
        """Two different categories must not be equal."""
        assert RepoCategory.LLM != RepoCategory.AGENT

    def test_category_equal_to_its_string_value(self) -> None:
        """Since RepoCategory inherits str, it must equal its raw string value."""
        assert RepoCategory.AGENT == "Agent"

    @pytest.mark.parametrize(
        "category",
        list(RepoCategory),
    )
    def test_category_is_hashable(self, category: RepoCategory) -> None:
        """Every RepoCategory must be hashable for use in sets and dicts."""
        category_set = {category}
        assert category in category_set
