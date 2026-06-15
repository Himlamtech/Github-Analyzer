"""Presentation tests for dashboard storytelling endpoints."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
import pytest

from src.domain.entities.external_news_item import ExternalNewsItem
from src.infrastructure.config import ExternalNewsSourceConfig, Settings, get_settings
from src.presentation.api.dashboard_routes import _get_dashboard_service
from src.presentation.api.intelligence_routes import (
    _get_dashboard_service as _get_intelligence_service,
)
from src.presentation.api.intelligence_routes import (
    _get_external_news_reader,
    _get_external_news_repository,
)
from src.presentation.api.routes import app

_NOW = datetime(2026, 3, 30, 12, 0, tzinfo=UTC)


class FakeDashboardService:
    @staticmethod
    def _repo_item() -> dict[str, object]:
        return {
            "repo_id": 1,
            "repo_full_name": "browser-use/browser-use",
            "repo_name": "browser-use",
            "html_url": "https://github.com/browser-use/browser-use",
            "description": "Browser agents for operator workflows.",
            "primary_language": "Python",
            "topics": ["browser-use", "agents"],
            "category": "Coding Agents & Automation",
            "stargazers_count": 50_000,
            "watchers_count": 50_000,
            "forks_count": 2_000,
            "open_issues_count": 40,
            "subscribers_count": 300,
            "owner_login": "browser-use",
            "owner_avatar_url": "",
            "license_name": "MIT",
            "github_created_at": _NOW,
            "github_pushed_at": _NOW,
            "rank": 1,
            "star_count_in_window": 1_200,
        }

    @staticmethod
    def _framework_repo_item() -> dict[str, object]:
        return {
            "repo_id": 2,
            "repo_full_name": "langchain-ai/langchain",
            "repo_name": "langchain",
            "html_url": "https://github.com/langchain-ai/langchain",
            "description": "Framework for LLM applications and agents.",
            "primary_language": "Python",
            "topics": ["langchain", "agents", "llm"],
            "category": "Developer Tooling",
            "stargazers_count": 110_000,
            "watchers_count": 110_000,
            "forks_count": 16_000,
            "open_issues_count": 120,
            "subscribers_count": 800,
            "owner_login": "langchain-ai",
            "owner_avatar_url": "",
            "license_name": "MIT",
            "github_created_at": _NOW,
            "github_pushed_at": _NOW,
            "rank": 2,
            "star_count_in_window": 700,
        }

    async def get_top_starred_repos(
        self,
        *,
        category: str | None,
        limit: int,
        days: int,
    ) -> list[dict[str, object]]:
        del days, category
        item = self._repo_item()
        item["star_count_in_window"] = 0
        return [item][:limit]

    async def get_top_repos(
        self,
        *,
        category: str | None,
        days: int,
        limit: int,
    ) -> list[dict[str, object]]:
        del category, days
        return [self._repo_item(), self._framework_repo_item()][:limit]

    async def get_trending(self, days: int, limit: int) -> list[dict[str, object]]:
        del days
        item = self._repo_item()
        item["growth_rank"] = 1
        framework_item = self._framework_repo_item()
        framework_item["growth_rank"] = 2
        return [item, framework_item][:limit]

    async def get_new_repos_reaching_star_threshold(
        self,
        *,
        threshold: int,
        limit: int,
    ) -> list[dict[str, object]]:
        assert threshold == 10_000
        item = self._repo_item()
        item["baseline_stars"] = 9_500
        item["current_stars"] = 10_800
        item["star_count_in_window"] = 1_300
        item["crossed_threshold_at"] = _NOW
        item["rank"] = 1
        return [item][:limit]

    async def get_shock_movers(
        self,
        *,
        days: int,
        absolute_limit: int,
        percentage_limit: int,
        min_baseline_stars: int,
    ) -> dict[str, object]:
        del absolute_limit, percentage_limit, min_baseline_stars
        item = {
            **self._repo_item(),
            "previous_star_count_in_window": 300,
            "unique_actors_in_window": 250,
            "weekly_percent_gain": 12.5,
            "window_over_window_ratio": 4.0,
        }
        return {
            "window_days": days,
            "absolute_movers": [dict(item, rank=1)],
            "percentage_movers": [dict(item, rank=1)],
        }

    async def get_topic_rotation(self, *, days: int, limit: int) -> list[dict[str, object]]:
        del days, limit
        return [
            {
                "topic": "browser-use",
                "current_star_count": 600,
                "previous_star_count": 120,
                "star_delta": 480,
                "repo_count": 14,
                "rank": 1,
            }
        ]


class FakeExternalNewsReader:
    async def fetch_latest(
        self,
        *,
        provider: str,
        url: str,
        source_type: str,
        limit: int,
    ) -> list[ExternalNewsItem]:
        del url, source_type
        return [
            ExternalNewsItem(
                source_id=f"{provider.lower()}-preview-1",
                provider=provider,
                title=f"{provider} browser agent launch",
                url="https://example.com/preview-1",
                published_at=_NOW,
                summary="Official preview summary for browser automation agents.",
            )
        ][:limit]


class FakeExternalNewsRepository:
    def __init__(self) -> None:
        self.items = [
            {
                "source_id": "openai-preview-1",
                "provider": "OpenAI",
                "title": "OpenAI browser agent launch",
                "url": "https://example.com/preview-1",
                "published_at": _NOW,
                "summary": "Official preview summary for browser automation agents.",
                "source_type": "rss",
                "event_type": "launch",
                "linked_entities": ["OpenAI", "Browser Use"],
                "linked_categories": ["Coding Agents & Automation"],
                "linked_repo_full_names": ["browser-use/browser-use"],
                "linked_framework_ids": ["browser-use", "openai-agents"],
                "quality_score": 90.0,
                "is_quarantined": False,
                "quarantine_reason": None,
            },
            {
                "source_id": "https://example.com/preview-1",
                "provider": "OpenAI",
                "title": "OpenAI URL-shaped source launch",
                "url": "https://example.com/preview-1",
                "published_at": _NOW,
                "summary": "Official URL-shaped source summary for browser automation agents.",
                "source_type": "rss",
                "event_type": "launch",
                "linked_entities": ["OpenAI", "Browser Use"],
                "linked_categories": ["Coding Agents & Automation"],
                "linked_repo_full_names": ["browser-use/browser-use"],
                "linked_framework_ids": ["browser-use", "openai-agents"],
                "quality_score": 88.0,
                "is_quarantined": False,
                "quarantine_reason": None,
            },
        ]
        self.health = [
            {
                "provider": "OpenAI",
                "source_url": "https://openai.com/news/rss.xml",
                "status": "ok",
                "fetched_count": 1,
                "error_message": None,
                "checked_at": datetime.now(tz=UTC) - timedelta(minutes=30),
            }
        ]

    async def upsert_items(self, items: list[ExternalNewsItem]) -> int:
        self.items = [
            {
                "source_id": item.source_id,
                "provider": item.provider,
                "title": item.title,
                "url": item.url,
                "published_at": item.published_at,
                "summary": item.summary,
                "source_type": item.source_type,
                "event_type": item.event_type,
                "linked_entities": list(item.linked_entities),
                "linked_categories": list(item.linked_categories),
                "linked_repo_full_names": list(item.linked_repo_full_names),
                "linked_framework_ids": list(item.linked_framework_ids),
                "quality_score": item.quality_score,
                "is_quarantined": item.is_quarantined,
                "quarantine_reason": item.quarantine_reason,
            }
            for item in items
        ]
        return len(items)

    async def append_source_health_snapshot(
        self,
        *,
        provider: str,
        source_url: str,
        status: str,
        fetched_count: int,
        error_message: str | None,
        checked_at: datetime,
    ) -> None:
        self.health = [
            {
                "provider": provider,
                "source_url": source_url,
                "status": status,
                "fetched_count": fetched_count,
                "error_message": error_message,
                "checked_at": checked_at,
            }
        ]

    async def list_latest_items(
        self,
        *,
        provider: str | None,
        limit: int,
        include_quarantined: bool = False,
    ) -> list[dict[str, object]]:
        rows = self.items
        if provider is not None:
            rows = [item for item in rows if item["provider"] == provider]
        if not include_quarantined:
            rows = [item for item in rows if not item["is_quarantined"]]
        return rows[:limit]

    async def get_item_by_source_id(self, source_id: str) -> dict[str, object] | None:
        for item in self.items:
            if item["source_id"] == source_id:
                return item
        return None

    async def list_latest_source_health(self) -> list[dict[str, object]]:
        return self.health


def _override_settings() -> object:
    base_settings = get_settings()
    return Settings(
        github_api_tokens=base_settings.github_api_tokens,
        github_api_base_url=base_settings.github_api_base_url,
        poll_interval_seconds=base_settings.poll_interval_seconds,
        kafka_bootstrap_servers=base_settings.kafka_bootstrap_servers,
        kafka_topic=base_settings.kafka_topic,
        kafka_retention_hours=base_settings.kafka_retention_hours,
        clickhouse_host=base_settings.clickhouse_host,
        clickhouse_port=base_settings.clickhouse_port,
        clickhouse_user=base_settings.clickhouse_user,
        clickhouse_password=base_settings.clickhouse_password,
        clickhouse_database=base_settings.clickhouse_database,
        parquet_base_path=base_settings.parquet_base_path,
        checkpoint_base_path=base_settings.checkpoint_base_path,
        spark_master=base_settings.spark_master,
        spark_driver_memory=base_settings.spark_driver_memory,
        spark_executor_memory=base_settings.spark_executor_memory,
        spark_parquet_max_records_per_file=base_settings.spark_parquet_max_records_per_file,
        spark_parquet_target_partitions_per_batch=(
            base_settings.spark_parquet_target_partitions_per_batch
        ),
        repo_metadata_path=base_settings.repo_metadata_path,
        repo_catalog_path=base_settings.repo_catalog_path,
        repo_discovery_min_stars=base_settings.repo_discovery_min_stars,
        repo_discovery_max_shard_size=base_settings.repo_discovery_max_shard_size,
        repo_discovery_start_date=base_settings.repo_discovery_start_date,
        news_intelligence_mode="hybrid",
        news_intelligence_sync_enabled=True,
        news_intelligence_sources=[
            ExternalNewsSourceConfig(
                provider="OpenAI",
                url="https://openai.com/news/rss.xml",
                source_type="rss",
                enabled=True,
            )
        ],
        log_level=base_settings.log_level,
    )


@pytest.fixture
def client() -> TestClient:
    fake_repository = FakeExternalNewsRepository()
    app.dependency_overrides[get_settings] = _override_settings
    app.dependency_overrides[_get_dashboard_service] = lambda: FakeDashboardService()
    app.dependency_overrides[_get_intelligence_service] = lambda: FakeDashboardService()
    app.dependency_overrides[_get_external_news_reader] = lambda: FakeExternalNewsReader()
    app.dependency_overrides[_get_external_news_repository] = lambda: fake_repository
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_breakout_route_returns_intelligence_scores(client: TestClient) -> None:
    response = client.get("/intelligence/breakout", params={"limit": 5, "days": 7})

    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["repo"]["repo_full_name"] == "browser-use/browser-use"
    assert payload[0]["breakout_score"] > 0
    assert payload[0]["confidence_score"] > 0
    assert payload[0]["explanation_trace"]


def test_rotation_route_returns_intelligence_categories(client: TestClient) -> None:
    response = client.get("/intelligence/rotation", params={"limit": 5, "days": 7})

    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["category"] == "Coding Agents & Automation"
    assert payload[0]["confidence_score"] > 0
    assert payload[0]["rotation_drivers"]


def test_framework_radar_route_returns_snapshot(client: TestClient) -> None:
    response = client.get("/intelligence/framework-radar")

    assert response.status_code == 200
    payload = response.json()
    assert payload["frameworks"]
    assert any(item["framework_id"] == "langchain" for item in payload["frameworks"])
    assert payload["winners"]
    assert payload["warnings"]


def test_news_impact_route_returns_computed_snapshot(client: TestClient) -> None:
    response = client.get("/intelligence/news-impact")

    assert response.status_code == 200
    payload = response.json()
    assert payload
    assert payload[0]["event_id"] == "openai-preview-1"
    assert payload[0]["source"] == "persisted_external_news"
    assert payload[0]["linked_repos"] == ["browser-use/browser-use"]
    assert payload[0]["linked_frameworks"] == ["browser-use", "openai-agents"]
    assert payload[0]["impact_curve"]
    assert payload[0]["top_impacted_repos"]


def test_news_impact_detail_route_returns_single_event(client: TestClient) -> None:
    response = client.get("/intelligence/news-impact/openai-preview-1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["event_id"] == "openai-preview-1"
    assert payload["quality_score"] > 0
    assert payload["linked_frameworks"] == ["browser-use", "openai-agents"]


def test_news_impact_detail_query_route_handles_simple_source_id(client: TestClient) -> None:
    response = client.get(
        "/intelligence/news-impact/detail",
        params={"source_id": "openai-preview-1"},
    )

    assert response.status_code == 200
    assert response.json()["event_id"] == "openai-preview-1"


def test_news_impact_detail_query_route_handles_url_shaped_source_id(
    client: TestClient,
) -> None:
    source_id = "https://example.com/preview-1"

    response = client.get(
        "/intelligence/news-impact/detail",
        params={"source_id": source_id},
    )

    assert response.status_code == 200
    assert response.json()["event_id"] == source_id


def test_news_impact_legacy_detail_path_handles_url_shaped_source_id(
    client: TestClient,
) -> None:
    response = client.get("/intelligence/news-impact/https://example.com/preview-1")

    assert response.status_code == 200
    assert response.json()["event_id"] == "https://example.com/preview-1"


def test_news_impact_legacy_detail_path_returns_controlled_not_found(
    client: TestClient,
) -> None:
    response = client.get("/intelligence/news-impact/https://example.com/unknown")

    assert response.status_code == 404
    assert response.json()["detail"] == "News impact event not found"


def test_news_impact_readiness_route_returns_source_status(client: TestClient) -> None:
    response = client.get("/intelligence/news-impact/readiness")

    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "hybrid"
    assert payload["status"] == "ready"
    assert payload["freshness_status"] == "healthy"
    assert payload["configured_source_count"] == 1
    assert payload["enabled_source_count"] == 1
    assert payload["healthy_source_count"] == 1
    assert payload["stale_source_count"] == 0
    assert payload["sources"][0]["freshness_status"] == "healthy"
    assert not payload["missing_requirements"]


def test_news_impact_source_preview_route_returns_latest_official_items(
    client: TestClient,
) -> None:
    response = client.get("/intelligence/news-impact/sources/preview")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["provider"] == "OpenAI"
    assert payload[0]["items"][0]["source_id"] == "openai-preview-1"


def test_news_impact_source_sync_route_persists_items(client: TestClient) -> None:
    response = client.post("/intelligence/news-impact/sources/sync")

    assert response.status_code == 200
    payload = response.json()
    assert payload["persisted_item_count"] == 1
    assert payload["quarantined_item_count"] == 0
    assert payload["source_health"][0]["status"] == "ok"


def test_news_impact_source_latest_route_returns_persisted_items(client: TestClient) -> None:
    response = client.get("/intelligence/news-impact/sources/latest")

    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["source_id"] == "openai-preview-1"
    assert payload[0]["event_type"] == "launch"
    assert payload[0]["linked_repos"] == ["browser-use/browser-use"]


def test_news_impact_source_health_route_returns_latest_snapshots(client: TestClient) -> None:
    response = client.get("/intelligence/news-impact/sources/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["provider"] == "OpenAI"
    assert payload[0]["status"] == "ok"


def test_shock_movers_route_returns_market_lists(client: TestClient) -> None:
    response = client.get("/dashboard/shock-movers", params={"days": 7})

    assert response.status_code == 200
    assert response.json()["absolute_movers"][0]["repo"]["repo_full_name"] == (
        "browser-use/browser-use"
    )


def test_top_starred_route_returns_all_time_star_leaders(client: TestClient) -> None:
    response = client.get("/dashboard/top-starred-repos", params={"limit": 5, "days": 90})

    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["repo"]["repo_full_name"] == "browser-use/browser-use"
    assert payload[0]["repo"]["stargazers_count"] == 50_000
    assert payload[0]["star_count_in_window"] == 0


def test_trending_route_returns_current_week_growth_rank(client: TestClient) -> None:
    response = client.get("/dashboard/trending", params={"limit": 10})

    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["repo"]["repo_full_name"] == "browser-use/browser-use"
    assert payload[0]["star_count_in_window"] == 1_200
    assert payload[0]["growth_rank"] == 1


def test_new_repos_reaching_10k_route_returns_weekly_milestones(
    client: TestClient,
) -> None:
    response = client.get("/dashboard/new-repos-reaching-10k", params={"limit": 5})

    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["repo"]["repo_full_name"] == "browser-use/browser-use"
    assert payload[0]["baseline_stars"] == 9_500
    assert payload[0]["current_stars"] == 10_800
    assert payload[0]["star_count_in_window"] == 1_300
    assert payload[0]["crossed_threshold_at"] == _NOW.isoformat().replace("+00:00", "Z")
    assert payload[0]["rank"] == 1


def test_topic_rotation_route_returns_ranked_topics(client: TestClient) -> None:
    response = client.get("/dashboard/topic-rotation", params={"days": 7})

    assert response.status_code == 200
    assert response.json()[0]["topic"] == "browser-use"
    assert response.json()[0]["star_delta"] == 480
