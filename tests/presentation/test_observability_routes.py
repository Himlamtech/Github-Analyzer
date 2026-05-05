"""Tests for health and observability API routes."""

from __future__ import annotations

from fastapi.testclient import TestClient

from src.infrastructure.config import get_settings
from src.presentation.api import routes as routes_module
from src.presentation.api.routes import app


def test_health_returns_request_id(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(routes_module, "start_metrics_server", lambda port: None)
    monkeypatch.setattr(routes_module, "setup_tracing", lambda app, settings: None)
    monkeypatch.setattr(routes_module, "shutdown_tracing", lambda: None)

    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.headers["X-Request-Id"]


def test_metrics_health_reflects_settings(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    settings = get_settings().model_copy(update={"metrics_enabled": True, "metrics_port": 19091})
    monkeypatch.setattr(routes_module, "start_metrics_server", lambda port: None)
    monkeypatch.setattr(routes_module, "setup_tracing", lambda app, settings: None)
    monkeypatch.setattr(routes_module, "shutdown_tracing", lambda: None)
    app.dependency_overrides[get_settings] = lambda: settings

    try:
        with TestClient(app) as client:
            response = client.get("/metrics-health")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"enabled": True, "port": 19091}
