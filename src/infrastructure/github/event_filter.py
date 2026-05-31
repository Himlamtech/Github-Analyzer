"""GitHub event admission filter.

The filter now validates only the structural requirements needed by the ingest
pipeline. It does not inspect repository topics or descriptions.
"""

from __future__ import annotations

import structlog

logger = structlog.get_logger(__name__)


class RepositoryEventFilter:
    """Accept structurally valid GitHub events for downstream ingestion."""

    @staticmethod
    def _coerce_int(value: object) -> int:
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        if isinstance(value, str):
            try:
                return int(value)
            except ValueError:
                return 0
        return 0

    @staticmethod
    def _as_dict(value: object) -> dict[str, object]:
        return value if isinstance(value, dict) else {}

    def should_ingest(self, event: dict[str, object]) -> bool:
        """Return True when the event is valid enough to retain."""
        actor = self._as_dict(event.get("actor"))
        repo = self._as_dict(event.get("repo"))
        actor_login = str(actor.get("login") or "").strip()
        repo_name = str(repo.get("name") or "").strip()
        repo_id = self._coerce_int(repo.get("id"))

        if not actor_login or not repo_name or repo_id <= 0:
            logger.debug(
                "repository_event_filter.discarded_invalid_event",
                event_id=str(event.get("id") or ""),
                actor_login=actor_login,
                repo_name=repo_name,
                repo_id=repo_id,
            )
            return False

        logger.debug(
            "repository_event_filter.accepted",
            repo=repo_name,
        )
        return True


PopularRepoFilter = RepositoryEventFilter
