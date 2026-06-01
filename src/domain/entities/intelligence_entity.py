"""Structured intelligence registry entity definitions."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class IntelligenceEntity:
    """Single structured entity used across intelligence use cases."""

    entity_id: str
    entity_type: str
    display_name: str
    aliases: tuple[str, ...] = ()
    categories: tuple[str, ...] = ()
    repo_full_names: tuple[str, ...] = ()
    framework_ids: tuple[str, ...] = ()
