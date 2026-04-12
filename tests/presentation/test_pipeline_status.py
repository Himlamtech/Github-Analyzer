"""Presentation tests for the pipeline status diagnostic endpoint."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Protocol, cast

from fastapi.testclient import TestClient
import pytest

from src.infrastructure.config import get_settings
from src.presentation.api import routes as routes_module
from src.presentation.api.routes import _get_clickhouse_repo, app

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path


class _SupportsStatusCode(Protocol):
    """Structural type for OpenTelemetry status-like objects."""

    status_code: object
    description: str | None


class FakeClickHouseRepo:
    """Async stub returning a fixed latest-event timestamp."""

    def __init__(self, max_created_at: float | None) -> None:
        self._max_created_at = max_created_at

    async def get_max_created_at(self) -> float | None:
        return self._max_created_at


class _FakeSpan:
    """Minimal span recorder for endpoint-level tracing tests."""

    def __init__(self, name: str, collector: list[dict[str, object]]) -> None:
        self._name = name
        self._collector = collector
        self._attributes: dict[str, object] = {}
        self._status_code: str | None = None
        self._status_description: str | None = None

    def __enter__(self) -> _FakeSpan:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self._collector.append(
            {
                "name": self._name,
                "attributes": dict(self._attributes),
                "status_code": self._status_code,
                "status_description": self._status_description,
            }
        )

    def set_attribute(self, key: str, value: object) -> None:
        self._attributes[key] = value

    def set_status(self, status: _SupportsStatusCode) -> None:
        self._status_code = getattr(getattr(status, "status_code", None), "name", None)
        self._status_description = getattr(status, "description", None)


class FakeTracer:
    """Tracer stub that records child spans created inside the endpoint."""

    def __init__(self) -> None:
        self.spans: list[dict[str, object]] = []

    def start_as_current_span(self, name: str) -> _FakeSpan:
        return _FakeSpan(name, self.spans)


class FakeRootSpan:
    """Root span stub so the endpoint can annotate the current request span."""

    def __init__(self) -> None:
        self.attributes: dict[str, object] = {}
        self.status_code: str | None = None
        self.status_description: str | None = None

    def set_attribute(self, key: str, value: object) -> None:
        self.attributes[key] = value

    def set_status(self, status: _SupportsStatusCode) -> None:
        self.status_code = getattr(getattr(status, "status_code", None), "name", None)
        self.status_description = getattr(status, "description", None)


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    settings = get_settings().model_copy(update={"parquet_base_path": str(tmp_path / "raw")})

    app.dependency_overrides[get_settings] = lambda: settings
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_pipeline_status_stale_pipeline_returns_200_and_marks_trace_error(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stale_seconds = 601.0
    fake_tracer = FakeTracer()
    root_span = FakeRootSpan()
    trace_module = cast("object", routes_module.__dict__["trace"])

    app.dependency_overrides[_get_clickhouse_repo] = lambda: FakeClickHouseRepo(
        time.time() - stale_seconds,
    )
    monkeypatch.setattr(routes_module, "tracer", fake_tracer)
    monkeypatch.setattr(trace_module, "get_current_span", lambda: root_span)
    monkeypatch.setattr(routes_module, "get_current_trace_id", lambda: None)

    response = client.get("/pipeline/status")

    assert response.status_code == 200
    assert response.json()["status"] == "degraded"
    assert response.json()["data_freshness_seconds"] >= stale_seconds - 5
    assert root_span.status_code == "ERROR"
    assert root_span.attributes["pipeline.status"] == "degraded"
    assert any(
        cast("str", span["name"]) == "pipeline_status.evaluate_status"
        and cast("dict[str, object]", span["attributes"]).get("pipeline.root_cause_hint")
        == "processing_pipeline_stalled"
        and cast("str | None", span["status_code"]) == "ERROR"
        for span in fake_tracer.spans
    )


def test_pipeline_status_healthy_pipeline_keeps_trace_ok(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    parquet_path = tmp_path / "raw"
    parquet_path.mkdir(parents=True, exist_ok=True)
    settings = get_settings().model_copy(update={"parquet_base_path": str(parquet_path)})
    fake_tracer = FakeTracer()
    root_span = FakeRootSpan()
    trace_module = cast("object", routes_module.__dict__["trace"])

    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[_get_clickhouse_repo] = lambda: FakeClickHouseRepo(time.time() - 30.0)
    monkeypatch.setattr(routes_module, "tracer", fake_tracer)
    monkeypatch.setattr(trace_module, "get_current_span", lambda: root_span)
    monkeypatch.setattr(routes_module, "get_current_trace_id", lambda: None)

    response = client.get("/pipeline/status")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert root_span.status_code is None
    assert root_span.attributes["pipeline.status"] == "healthy"
