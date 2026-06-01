"""Presentation tests for dashboard storytelling endpoints."""

from __future__ import annotations

from datetime import UTC, datetime

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
            "description": "Browser agents.",
            "primary_language": "Python",
            "topics": ["browser-use", "agents"],
            "category": "Agent",
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

    async def get_top_starred_repos(
        self,
        *,
        category: str | None,
        limit: int,
        days: int,
    ) -> list[dict[str, object]]:
        del days
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
        return [self._repo_item()][:limit]

    async def get_trending(self, days: int, limit: int) -> list[dict[str, object]]:
        del days
        item = self._repo_item()
        item["growth_rank"] = 1
        return [item][:limit]

    async def get_shock_movers(
        self,
        *,
        days: int,
        absolute_limit: int,
        percentage_limit: int,
        min_baseline_stars: int,
    ) -> dict[str, object]:
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
                title=f"{provider} source preview",
                url="https://example.com/preview-1",
                published_at=_NOW,
                summary="Official preview summary.",
            )
        ][:limit]


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
    app.dependency_overrides[get_settings] = _override_settings
    app.dependency_overrides[_get_dashboard_service] = lambda: FakeDashboardService()
    app.dependency_overrides[_get_intelligence_service] = lambda: FakeDashboardService()
    app.dependency_overrides[_get_external_news_reader] = lambda: FakeExternalNewsReader()
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
    assert payload[0]["category"] == "Browser Use"
    assert payload[0]["confidence_score"] > 0
    assert payload[0]["rotation_drivers"]


def test_framework_radar_route_returns_snapshot(client: TestClient) -> None:
    response = client.get("/intelligence/framework-radar")

    assert response.status_code == 200
    payload = response.json()
    assert payload["frameworks"]
    assert payload["frameworks"][0]["framework_id"] == "langchain"
    assert payload["winners"]
    assert payload["warnings"]


def test_news_impact_route_returns_curated_snapshot(client: TestClient) -> None:
    response = client.get("/intelligence/news-impact")

    assert response.status_code == 200
    payload = response.json()
    assert payload
    assert payload[0]["event_id"] == "anthropic-computer-use-2024-10-22"
    assert payload[0]["impact_curve"]
    assert payload[0]["top_impacted_repos"]


def test_news_impact_readiness_route_returns_source_status(client: TestClient) -> None:
    response = client.get("/intelligence/news-impact/readiness")

    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "hybrid"
    assert payload["status"] == "ready"
    assert payload["configured_source_count"] == 1
    assert payload["enabled_source_count"] == 1
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


def test_weekly_brief_route_returns_snapshot(client: TestClient) -> None:
    response = client.get("/intelligence/weekly-brief/latest")

    assert response.status_code == 200
    payload = response.json()
    assert payload["brief_id"] == "weekly-signal-vol-14"
    assert payload["pillars"]
    assert payload["summary_chart_data"]
    assert payload["regional_indicators"]


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


def test_topic_rotation_route_returns_ranked_topics(client: TestClient) -> None:
    response = client.get("/dashboard/topic-rotation", params={"days": 7})

    assert response.status_code == 200
    assert response.json()[0]["topic"] == "browser-use"
    assert response.json()[0]["star_delta"] == 480
