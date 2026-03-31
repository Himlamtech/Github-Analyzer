"""Presentation tests for dashboard storytelling endpoints."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi.testclient import TestClient
import pytest

from src.infrastructure.config import get_settings
from src.presentation.api.dashboard_routes import _get_dashboard_service
from src.presentation.api.routes import app

_NOW = datetime(2026, 3, 30, 12, 0, tzinfo=UTC)


class FakeDashboardService:
    async def get_shock_movers(
        self,
        *,
        days: int,
        absolute_limit: int,
        percentage_limit: int,
        min_baseline_stars: int,
    ) -> dict[str, object]:
        item = {
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


def _override_settings() -> object:
    return get_settings()


@pytest.fixture
def client() -> TestClient:
    app.dependency_overrides[get_settings] = _override_settings
    app.dependency_overrides[_get_dashboard_service] = lambda: FakeDashboardService()
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_shock_movers_route_returns_market_lists(client: TestClient) -> None:
    response = client.get("/dashboard/shock-movers", params={"days": 7})

    assert response.status_code == 200
    assert response.json()["absolute_movers"][0]["repo"]["repo_full_name"] == (
        "browser-use/browser-use"
    )


def test_topic_rotation_route_returns_ranked_topics(client: TestClient) -> None:
    response = client.get("/dashboard/topic-rotation", params={"days": 7})

    assert response.status_code == 200
    assert response.json()[0]["topic"] == "browser-use"
    assert response.json()[0]["star_delta"] == 480
