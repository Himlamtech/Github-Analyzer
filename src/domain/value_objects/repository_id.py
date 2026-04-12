"""RepositoryId value object — typed, validated identity for a GitHub repository.

Stored as a frozen dataclass so it is hashable and can be used as a dict key
or Kafka partition key without risk of mutation.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.domain.exceptions import InvalidRepositoryIdError

_MAX_REPO_ID = 10**12  # GitHub numeric IDs are well below this ceiling


@dataclass(frozen=True, slots=True)
class RepositoryId:
    """Immutable identifier for a GitHub repository.

    Wraps the integer repository ID returned by the GitHub API.
    Equality and hashing are derived from the numeric ``value``.

    Attributes:
        value: The positive integer repository ID assigned by GitHub.
        name: The ``owner/repo`` string representation (e.g. "torvalds/linux").
    """

    value: int
    name: str

    def __post_init__(self) -> None:
        if self.value <= 0 or self.value > _MAX_REPO_ID:
            raise InvalidRepositoryIdError(
                f"Repository ID must be a positive integer ≤ {_MAX_REPO_ID}, got {self.value!r}."
            )
        if not self.name or "/" not in self.name:
            raise InvalidRepositoryIdError(
                f"Repository name must be in 'owner/repo' format, got {self.name!r}."
            )

    @classmethod
    def from_api(cls, repo_id: int, repo_name: str) -> RepositoryId:
        """Construct a RepositoryId from raw GitHub API response fields.

        Args:
            repo_id: The integer ``repo.id`` from the API response.
            repo_name: The ``repo.name`` string (``owner/repo`` format).

        Returns:
            A validated, immutable RepositoryId instance.

        Raises:
            InvalidRepositoryIdError: If either argument fails validation.
        """
        return cls(value=repo_id, name=repo_name)

    @property
    def owner(self) -> str:
        """Return the repository owner portion of the name."""
        return self.name.split("/")[0]

    @property
    def repo(self) -> str:
        """Return the repository short-name portion."""
        return self.name.split("/")[1]

    def __str__(self) -> str:
        return self.name
