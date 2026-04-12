"""Unit tests for repo-first catalog discovery."""

from __future__ import annotations

from datetime import date
import json
from typing import TYPE_CHECKING

from university.github.src.application.use_cases.discover_repo_catalog import DiscoverRepoCatalogUseCase

if TYPE_CHECKING:
    from pathlib import Path


class FakeRepoCatalogClient:
    """Stub discovery client with deterministic shard responses."""

    def __init__(
        self,
        *,
        max_stars: int,
        counts: dict[tuple[int, int, str, str], int],
        search_pages: dict[tuple[int, int, str, str, int], list[dict[str, object]]],
    ) -> None:
        self._max_stars = max_stars
        self._counts = counts
        self._search_pages = search_pages
        self.count_calls: list[tuple[int, int, str, str]] = []

    async def get_repository_search_max_stars(self, min_stars: int) -> int:
        assert min_stars >= 1
        return self._max_stars

    async def count_repositories(
        self,
        *,
        min_stars: int,
        max_stars: int,
        created_after: date,
        created_before: date,
    ) -> int:
        key = (
            min_stars,
            max_stars,
            created_after.isoformat(),
            created_before.isoformat(),
        )
        self.count_calls.append(key)
        return self._counts.get(key, 0)

    async def search_repositories(
        self,
        *,
        min_stars: int,
        max_stars: int,
        created_after: date,
        created_before: date,
        page: int,
        per_page: int = 100,
    ) -> list[dict[str, object]]:
        assert per_page == 100
        return self._search_pages.get(
            (
                min_stars,
                max_stars,
                created_after.isoformat(),
                created_before.isoformat(),
                page,
            ),
            [],
        )

    async def fetch_repository_metadata(
        self,
        repo_full_name: str,
        *,
        rank: int | None = None,
    ) -> dict[str, object]:
        return {
            "id": hash(repo_full_name) % 1_000_000,
            "full_name": repo_full_name,
            "name": repo_full_name.split("/")[-1],
            "html_url": f"https://github.com/{repo_full_name}",
            "stargazers_count": {
                "openai/gpt-5": 12000,
                "langchain-ai/langchain": 11400,
                "huggingface/transformers": 11100,
                "anthropic/claude-cookbooks": 10000,
                "mistralai/cookbook": 10000,
                "torvalds/linux": 150000,
            }[repo_full_name],
            "rank": rank,
        }


def _snapshot_file(repo_catalog_dir: Path) -> Path:
    return repo_catalog_dir / "latest.json"


class TestDiscoverRepoCatalogUseCase:
    async def test_execute_splits_star_ranges_deduplicates_and_writes_outputs(
        self,
        tmp_path: Path,
    ) -> None:
        counts = {
            (10000, 12000, "2024-01-01", "2024-01-10"): 120,
            (10000, 11000, "2024-01-01", "2024-01-10"): 40,
            (11001, 12000, "2024-01-01", "2024-01-10"): 80,
            (11001, 11500, "2024-01-01", "2024-01-10"): 30,
            (11501, 12000, "2024-01-01", "2024-01-10"): 50,
        }
        search_pages = {
            (10000, 11000, "2024-01-01", "2024-01-10", 1): [
                {
                    "full_name": "huggingface/transformers",
                    "html_url": "https://github.com/huggingface/transformers",
                    "stargazers_count": 11100,
                }
            ],
            (11001, 11500, "2024-01-01", "2024-01-10", 1): [
                {
                    "full_name": "langchain-ai/langchain",
                    "html_url": "https://github.com/langchain-ai/langchain",
                    "stargazers_count": 11400,
                }
            ],
            (11501, 12000, "2024-01-01", "2024-01-10", 1): [
                {
                    "full_name": "openai/gpt-5",
                    "html_url": "https://github.com/openai/gpt-5",
                    "stargazers_count": 12000,
                },
                {
                    "full_name": "langchain-ai/langchain",
                    "html_url": "https://github.com/langchain-ai/langchain",
                    "stargazers_count": 11400,
                },
            ],
        }
        client = FakeRepoCatalogClient(
            max_stars=12000,
            counts=counts,
            search_pages=search_pages,
        )
        catalog_dir = tmp_path / "catalog"
        repo_dir = tmp_path / "repos"
        use_case = DiscoverRepoCatalogUseCase(
            discovery_client=client,
            repo_catalog_dir=str(catalog_dir),
            repo_metadata_dir=str(repo_dir),
            min_stars=10000,
            max_shard_size=50,
            start_date=date(2024, 1, 1),
            today=date(2024, 1, 10),
        )

        discovered = await use_case.execute()

        assert discovered == 3
        assert (repo_dir / "openai__gpt-5.json").exists()
        assert (repo_dir / "langchain-ai__langchain.json").exists()
        assert (repo_dir / "huggingface__transformers.json").exists()

        snapshot = json.loads(_snapshot_file(catalog_dir).read_text(encoding="utf-8"))
        assert snapshot["repo_count"] == 3
        assert len(snapshot["shards"]) == 3
        assert [repo["full_name"] for repo in snapshot["repos"]] == [
            "openai/gpt-5",
            "langchain-ai/langchain",
            "huggingface/transformers",
        ]

        openai_repo = json.loads((repo_dir / "openai__gpt-5.json").read_text(encoding="utf-8"))
        assert openai_repo["rank"] == 1

    async def test_execute_splits_by_created_date_when_star_bucket_cannot_split(
        self,
        tmp_path: Path,
    ) -> None:
        counts = {
            (10000, 10000, "2024-01-01", "2024-01-05"): 120,
            (10000, 10000, "2024-01-01", "2024-01-03"): 40,
            (10000, 10000, "2024-01-04", "2024-01-05"): 40,
        }
        search_pages = {
            (10000, 10000, "2024-01-01", "2024-01-03", 1): [
                {
                    "full_name": "anthropic/claude-cookbooks",
                    "html_url": "https://github.com/anthropic/claude-cookbooks",
                    "stargazers_count": 10000,
                }
            ],
            (10000, 10000, "2024-01-04", "2024-01-05", 1): [
                {
                    "full_name": "mistralai/cookbook",
                    "html_url": "https://github.com/mistralai/cookbook",
                    "stargazers_count": 10000,
                }
            ],
        }
        client = FakeRepoCatalogClient(
            max_stars=10000,
            counts=counts,
            search_pages=search_pages,
        )
        use_case = DiscoverRepoCatalogUseCase(
            discovery_client=client,
            repo_catalog_dir=str(tmp_path / "catalog"),
            repo_metadata_dir=str(tmp_path / "repos"),
            min_stars=10000,
            max_shard_size=50,
            start_date=date(2024, 1, 1),
            today=date(2024, 1, 5),
        )

        discovered = await use_case.execute()

        assert discovered == 2
        assert (10000, 10000, "2024-01-01", "2024-01-05") in client.count_calls
        assert (10000, 10000, "2024-01-01", "2024-01-03") in client.count_calls
        assert (10000, 10000, "2024-01-04", "2024-01-05") in client.count_calls

    async def test_execute_persists_high_star_non_ai_repo(
        self,
        tmp_path: Path,
    ) -> None:
        counts = {
            (10000, 150000, "2024-01-01", "2024-01-10"): 1,
        }
        search_pages = {
            (10000, 150000, "2024-01-01", "2024-01-10", 1): [
                {
                    "full_name": "torvalds/linux",
                    "html_url": "https://github.com/torvalds/linux",
                    "stargazers_count": 150000,
                }
            ],
        }
        client = FakeRepoCatalogClient(
            max_stars=150000,
            counts=counts,
            search_pages=search_pages,
        )
        use_case = DiscoverRepoCatalogUseCase(
            discovery_client=client,
            repo_catalog_dir=str(tmp_path / "catalog"),
            repo_metadata_dir=str(tmp_path / "repos"),
            min_stars=10000,
            max_shard_size=50,
            start_date=date(2024, 1, 1),
            today=date(2024, 1, 10),
        )

        discovered = await use_case.execute()

        assert discovered == 1
        assert (tmp_path / "repos" / "torvalds__linux.json").exists()
