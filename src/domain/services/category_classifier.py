"""Repository category resolver.

Repository classification has been reduced to a neutral fallback. The service
is kept as a compatibility seam for metadata sync and dashboard code paths, and
it deterministically returns the neutral fallback category for every repository.
"""

from __future__ import annotations

from src.domain.value_objects.repo_category import RepoCategory


class CategoryClassifier:
    """Resolve repository metadata into the neutral fallback category."""

    def classify(
        self,
        topics: list[str],
        description: str,
    ) -> RepoCategory:
        """Return the only supported category.

        Args:
            topics: Repository topics. Retained for signature compatibility.
            description: Repository description. Retained for signature compatibility.
        """
        del topics
        del description
        return RepoCategory.OTHER
