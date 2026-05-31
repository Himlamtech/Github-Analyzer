"""Presentation tests for the pipeline status diagnostic endpoint."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from fastapi.testclient import TestClient
import pytest

from src.infrastructure.config import Settings, get_settings
from src.presentation.api.routes import _get_clickhouse_repo, app

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path


class FakeClickHouseRepo:
    """Async stub returning a fixed latest-event timestamp."""

    def __init__(self, max_created_at: float | None) -> None:
        self._max_created_at = max_created_at

    async def get_max_created_at(self) -> float | None:
        return self._max_created_at


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    settings = Settings(
        github_api_tokens="test-token",
        clickhouse_password="test-password",
        parquet_base_path=str(tmp_path / "raw"),
    )

    app.dependency_overrides[get_settings] = lambda: settings
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_pipeline_status_stale_pipeline_returns_200_when_pipeline_is_stale(
    client: TestClient,
) -> None:
    stale_seconds = 601.0
    app.dependency_overrides[_get_clickhouse_repo] = lambda: FakeClickHouseRepo(
        time.time() - stale_seconds,
    )

    response = client.get("/pipeline/status")

    assert response.status_code == 200
    assert response.json()["status"] == "degraded"
    assert response.json()["data_freshness_seconds"] >= stale_seconds - 5


def test_pipeline_status_healthy_pipeline_returns_healthy(
    client: TestClient,
    tmp_path: Path,
) -> None:
    parquet_path = tmp_path / "raw"
    parquet_path.mkdir(parents=True, exist_ok=True)
    settings = Settings(
        github_api_tokens="test-token",
        clickhouse_password="test-password",
        parquet_base_path=str(parquet_path),
    )

    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[_get_clickhouse_repo] = lambda: FakeClickHouseRepo(time.time() - 30.0)

    response = client.get("/pipeline/status")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
