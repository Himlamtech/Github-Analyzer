"""Tests for the curated framework radar snapshot use case."""

from __future__ import annotations

from src.application.use_cases.get_framework_radar_snapshot import (
    GetFrameworkRadarSnapshotUseCase,
)


def test_execute_returns_framework_radar_snapshot() -> None:
    use_case = GetFrameworkRadarSnapshotUseCase()

    result = use_case.execute()

    assert result.frameworks
    assert result.frameworks[0].framework_id == "langchain"
    assert result.frameworks[0].velocity_score >= 0.0
    assert result.winners
    assert result.warnings
