"""Mapper between raw GitHub API dicts, DTOs, and domain entities.

Responsibility: translate data representations across layer boundaries.
All mapping logic is centralised here; no parsing occurs in use cases or
domain entities.
"""

from __future__ import annotations

from typing import cast

import orjson

from src.application.dtos.github_event_dto import GithubEventInputDTO, GithubEventOutputDTO
from src.domain.entities.github_event import GithubEvent
from src.domain.exceptions import ValidationError
from src.domain.value_objects.event_type import EventType
from src.domain.value_objects.repository_id import RepositoryId


class GitHubEventMapper:
    """Stateless mapper for GitHub event data transformations.

    Design: each method handles exactly one transformation direction,
    keeping the translation logic explicit and independently testable.
    """

    @staticmethod
    def _as_dict(value: object) -> dict[str, object]:
        return cast("dict[str, object]", value) if isinstance(value, dict) else {}

    @staticmethod
    def _as_string_list(value: object) -> list[str]:
        if not isinstance(value, list):
            return []
        return [str(item) for item in value]

    @staticmethod
    def _as_int(value: object) -> int:
        return int(cast("int | float | str", value or 0))

    def to_input_dto(self, raw: dict[str, object]) -> GithubEventInputDTO:
        """Parse a raw GitHub API event dict into a validated input DTO.

        Args:
            raw: A single event object as returned by the GitHub Events API.

        Returns:
            A validated ``GithubEventInputDTO``.

        Raises:
            ValidationError: If any required field is missing or malformed.
        """
        try:
            actor = self._as_dict(raw.get("actor"))
            repo = self._as_dict(raw.get("repo"))
            payload = self._as_dict(raw.get("payload"))
            full_repo = self._as_dict(raw.get("_full_repo"))

            return GithubEventInputDTO(
                event_id=str(raw["id"]),
                event_type=str(raw["type"]),
                actor_id=int(str(actor["id"])),
                actor_login=str(actor["login"]),
                repo_id=int(str(repo["id"])),
                repo_name=str(repo["name"]),
                payload=payload,
                repo_stargazers_count=self._as_int(full_repo.get("stargazers_count")),
                repo_primary_language=str(full_repo.get("language") or ""),
                repo_topics=self._as_string_list(full_repo.get("topics")),
                repo_description=str(full_repo.get("description") or ""),
                repo_full_metadata_json=orjson.dumps(full_repo).decode(),
                repo_readme_text=str(raw.get("_repo_readme_text") or ""),
                repo_issues_json=orjson.dumps(raw.get("_repo_issues") or []).decode(),
                created_at=str(raw["created_at"]),
                public=bool(raw.get("public", True)),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValidationError(f"Cannot parse GitHub event from raw dict: {exc}") from exc

    def to_domain_entity(self, dto: GithubEventInputDTO) -> GithubEvent:
        """Map a validated input DTO to a GithubEvent domain entity.

        Args:
            dto: A validated ``GithubEventInputDTO``.

        Returns:
            A fully constructed ``GithubEvent`` aggregate root.

        Raises:
            ValidationError:    If domain invariants are violated.
            InvalidEventTypeError: If the event type is not supported.
        """
        event_type = EventType.from_raw(dto.event_type)
        repo_id = RepositoryId.from_api(
            repo_id=dto.repo_id,
            repo_name=dto.repo_name,
        )
        payload = dict(dto.payload)
        payload["_repo_stargazers_count"] = dto.repo_stargazers_count
        payload["_repo_primary_language"] = dto.repo_primary_language
        payload["_repo_topics"] = dto.repo_topics
        payload["_repo_description"] = dto.repo_description
        payload["_repo_full_metadata_json"] = dto.repo_full_metadata_json
        payload["_repo_readme_text"] = dto.repo_readme_text
        payload["_repo_issues_json"] = dto.repo_issues_json

        return GithubEvent(
            event_id=dto.event_id,
            event_type=event_type,
            repo_id=repo_id,
            actor_id=dto.actor_id,
            actor_login=dto.actor_login,
            created_at=dto.created_at,
            payload=payload,
            public=dto.public,
        )

    def to_output_dto(self, entity: GithubEvent) -> GithubEventOutputDTO:
        """Serialise a domain entity to the Kafka wire format.

        The ``payload`` dict is JSON-serialised using ``orjson`` (faster than
        stdlib json) and stored as a string column — the Spark schema treats it
        as opaque text that can be parsed downstream if needed.

        Args:
            entity: A ``GithubEvent`` aggregate root.

        Returns:
            A ``GithubEventOutputDTO`` ready for Kafka publication.
        """
        payload = dict(entity.payload)
        repo_stars = self._as_int(payload.pop("_repo_stargazers_count", 0))
        repo_primary_language = str(payload.pop("_repo_primary_language", "") or "")
        repo_topics = self._as_string_list(payload.pop("_repo_topics", []))
        repo_description = str(payload.pop("_repo_description", "") or "")
        repo_full_metadata_json = str(payload.pop("_repo_full_metadata_json", "") or "")
        repo_readme_text = str(payload.pop("_repo_readme_text", "") or "")
        repo_issues_json = str(payload.pop("_repo_issues_json", "") or "")

        return GithubEventOutputDTO(
            event_id=entity.event_id,
            event_type=str(entity.event_type),
            actor_id=entity.actor_id,
            actor_login=entity.actor_login,
            repo_id=entity.repo_id.value,
            repo_name=str(entity.repo_id),
            event_date=entity.event_date(),
            created_at=entity.created_at.isoformat(),
            payload_json=orjson.dumps(payload).decode(),
            repo_stargazers_count=repo_stars,
            repo_primary_language=repo_primary_language,
            repo_topics=repo_topics,
            repo_description=repo_description,
            repo_full_metadata_json=repo_full_metadata_json,
            repo_readme_text=repo_readme_text,
            repo_issues_json=repo_issues_json,
        )
