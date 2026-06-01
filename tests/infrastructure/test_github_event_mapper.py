from __future__ import annotations

from src.infrastructure.github.event_mapper import GitHubEventMapper


def test_to_output_dto_excludes_repo_metadata_blobs_from_hot_path() -> None:
    mapper = GitHubEventMapper()
    raw_event = {
        "id": "evt-1",
        "type": "WatchEvent",
        "actor": {"id": 1, "login": "alice"},
        "repo": {"id": 99, "name": "acme/widgets"},
        "payload": {"action": "started"},
        "created_at": "2026-06-01T12:00:00Z",
        "public": True,
        "_full_repo": {
            "stargazers_count": 123,
            "language": "Python",
            "topics": ["ai", "agents"],
            "description": "Widget repo",
            "full_name": "acme/widgets",
        },
        "_repo_readme_text": "README body",
        "_repo_issues": [{"id": 1, "title": "Issue"}],
    }

    dto = mapper.to_input_dto(raw_event)
    entity = mapper.to_domain_entity(dto)
    output = mapper.to_output_dto(entity)

    assert "_repo_full_metadata_json" not in entity.payload
    assert "_repo_readme_text" not in entity.payload
    assert "_repo_issues_json" not in entity.payload
    assert set(output.model_dump()) == {
        "event_id",
        "event_type",
        "actor_id",
        "actor_login",
        "repo_id",
        "repo_name",
        "event_date",
        "created_at",
        "payload_json",
        "repo_stargazers_count",
        "repo_primary_language",
        "repo_topics",
        "repo_description",
    }
