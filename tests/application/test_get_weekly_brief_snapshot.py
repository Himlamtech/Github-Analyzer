"""Tests for the curated weekly brief snapshot use case."""

from __future__ import annotations

from src.application.use_cases.get_weekly_brief_snapshot import (
    GetWeeklyBriefSnapshotUseCase,
)


def test_execute_returns_weekly_brief_snapshot() -> None:
    use_case = GetWeeklyBriefSnapshotUseCase()

    result = use_case.execute()

    assert result.brief_id == "weekly-signal-vol-14"
    assert result.pillars
    assert result.summary_chart_data
    assert result.regional_indicators
    assert result.authors
