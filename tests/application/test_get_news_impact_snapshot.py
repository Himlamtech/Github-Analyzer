"""Tests for the curated news impact snapshot use case."""

from __future__ import annotations

from src.application.use_cases.get_news_impact_snapshot import GetNewsImpactSnapshotUseCase


def test_execute_returns_news_impact_snapshot() -> None:
    use_case = GetNewsImpactSnapshotUseCase()

    result = use_case.execute()

    assert len(result) == 3
    assert result[0].event_id == "anthropic-computer-use-2024-10-22"
    assert result[0].impact_curve
    assert result[0].top_impacted_repos
    assert result[0].explanation_trace
