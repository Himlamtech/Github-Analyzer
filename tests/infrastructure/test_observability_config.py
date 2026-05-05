"""Tests for observability-related runtime settings."""

from __future__ import annotations

from src.infrastructure.config import get_settings


def test_settings_exposes_observability_defaults(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.delenv("METRICS_PORT", raising=False)
    monkeypatch.delenv("TRACING_GRAFANA_TEMPO_DATASOURCE_UID", raising=False)
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.metrics_enabled is True
    assert settings.metrics_port == 9091
    assert settings.pipeline_stale_threshold_seconds == 300
    assert settings.tracing_grafana_tempo_datasource_uid == "tempo_ds"

    get_settings.cache_clear()


def test_settings_splits_github_tokens(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("GITHUB_API_TOKENS", "one, two ,,three")
    get_settings.cache_clear()

    assert get_settings().github_tokens_list == ["one", "two", "three"]

    get_settings.cache_clear()
