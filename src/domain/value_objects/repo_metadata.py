"""RepoMetadata value object — typed 45-field schema for a GitHub repository.

Immutable. Used as the canonical cross-layer transfer object between
the JSON files on disk, the sync use case, and the ClickHouse repository.

Not an Entity: equality is by repo_full_name, no lifecycle management.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime

    from src.domain.value_objects.repo_category import RepoCategory


@dataclass(frozen=True)
class RepoOwner:
    """Flattened owner sub-object from GitHub API.

    Attributes:
        login:       GitHub username or organisation name.
        owner_id:    GitHub numeric user/org ID.
        owner_type:  ``"User"`` or ``"Organization"``.
        avatar_url:  URL of the owner avatar image.
    """

    login: str
    owner_id: int
    owner_type: str
    avatar_url: str


@dataclass(frozen=True)
class RepoLicense:
    """Flattened license sub-object from GitHub API.

    Attributes:
        key:      SPDX-compatible short key (e.g., ``"mit"``).
        name:     Full licence name (e.g., ``"MIT License"``).
        spdx_id:  SPDX identifier (e.g., ``"MIT"``).
    """

    key: str
    name: str
    spdx_id: str


@dataclass(frozen=True)
class RepoMetadata:
    """Full curated repository metadata — 45 fields from GitHub Repos API.

    Equality and hashing are by ``repo_full_name`` (``owner/repo``).
    All fields are immutable (``frozen=True``).

    Attributes:
        repo_id:           GitHub numeric repository ID.
        repo_full_name:    Canonical ``owner/repo`` identifier.
        repo_name:         Short repository name (without owner).
        node_id:           GraphQL global node ID.
        private:           ``True`` if the repository is private.
        html_url:          GitHub web URL.
        clone_url:         HTTPS clone URL.
        homepage:          Project homepage (self-reported).
        stargazers_count:  Current star count.
        watchers_count:    Current watcher count (== stargazers_count on GitHub).
        forks_count:       Current fork count.
        open_issues_count: Current open issues + PRs count.
        network_count:     Size of the fork network.
        subscribers_count: Watch subscriber count (stronger intent than starring).
        size_kb:           Repository disk size in kilobytes.
        github_created_at: Repository creation timestamp (UTC).
        github_updated_at: Last metadata update timestamp (UTC).
        github_pushed_at:  Last code push timestamp (UTC).
        primary_language:  Primary programming language (self-reported).
        topics:            Tuple of GitHub topic tags.
        visibility:        ``"public"``, ``"private"``, or ``"internal"``.
        default_branch:    Default branch name.
        description:       Repository description (self-reported).
        category:          Computed AI category from topics[].
        is_fork:           ``True`` if this repo is a fork.
        is_archived:       ``True`` if this repo is archived (read-only).
        is_disabled:       ``True`` if disabled by GitHub.
        has_issues:        Issues feature enabled.
        has_wiki:          Wiki feature enabled.
        has_discussions:   Discussions feature enabled.
        has_pages:         GitHub Pages enabled.
        allow_forking:     Public forking allowed.
        is_template:       Template repository flag.
        owner:             Flattened owner sub-object.
        license:           Flattened license sub-object.
        rank:              Optional ranking position (1-based), set by refresh job.
        fetched_at:        When this record was first fetched from GitHub API.
        refreshed_at:      When this record was last refreshed.
    """

    repo_id: int
    repo_full_name: str
    repo_name: str
    node_id: str
    private: bool

    html_url: str
    clone_url: str
    homepage: str

    stargazers_count: int
    watchers_count: int
    forks_count: int
    open_issues_count: int
    network_count: int
    subscribers_count: int
    size_kb: int

    github_created_at: datetime
    github_updated_at: datetime
    github_pushed_at: datetime

    primary_language: str
    topics: tuple[str, ...]
    visibility: str
    default_branch: str
    description: str
    category: RepoCategory

    is_fork: bool
    is_archived: bool
    is_disabled: bool
    has_issues: bool
    has_wiki: bool
    has_discussions: bool
    has_pages: bool
    allow_forking: bool
    is_template: bool

    owner: RepoOwner
    license: RepoLicense

    rank: int
    fetched_at: datetime
    refreshed_at: datetime

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, RepoMetadata):
            return NotImplemented
        return self.repo_full_name == other.repo_full_name

    def __hash__(self) -> int:
        return hash(self.repo_full_name)

    def __repr__(self) -> str:
        return (
            f"RepoMetadata(full_name={self.repo_full_name!r}, "
            f"stars={self.stargazers_count}, category={self.category})"
        )
