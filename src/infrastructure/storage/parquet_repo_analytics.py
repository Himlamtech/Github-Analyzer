"""Parquet-backed repository analytics helpers for degraded runtime paths."""

from __future__ import annotations

import json
from collections.abc import Iterator
from copy import deepcopy
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from threading import Event, Lock
from typing import Any

import pyarrow.parquet as pq

_CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "Agent": (
        "agent",
        "agents",
        "agentic",
        "browser-use",
        "autogen",
        "crewai",
        "multi-agent",
        "rag",
        "tool-calling",
        "mcp",
        "orchestr",
    ),
    "LLM": (
        "llm",
        "gpt",
        "claude",
        "llama",
        "mistral",
        "qwen",
        "gemini",
        "language model",
        "transformer",
        "prompt",
        "inference",
    ),
    "Multimodal": (
        "multimodal",
        "vision",
        "audio",
        "speech",
        "video",
        "voice",
        "asr",
        "tts",
        "vlm",
    ),
    "Diffusion": (
        "diffusion",
        "image generation",
        "text-to-image",
        "stable-diffusion",
        "sdxl",
        "controlnet",
        "flux",
        "comfyui",
    ),
    "DataEng": (
        "embedding",
        "embeddings",
        "vector-db",
        "vector database",
        "retrieval",
        "rerank",
        "search",
        "indexing",
        "dataset",
        "pipeline",
        "feature store",
        "warehouse",
    ),
}

_CACHE_TTL = timedelta(seconds=90)
_snapshot_cache_lock = Lock()
_snapshot_cache: dict[
    tuple[str, int, bool],
    tuple[datetime, list[dict[str, Any]]],
] = {}
_snapshot_inflight: dict[tuple[str, int, bool], Event] = {}
_timeseries_cache_lock = Lock()
_timeseries_cache: dict[
    tuple[str, str, int],
    tuple[datetime, list[dict[str, Any]]],
] = {}
_timeseries_inflight: dict[tuple[str, str, int], Event] = {}


def infer_repo_category(
    *,
    repo_full_name: str,
    description: str,
    primary_language: str,
    topics: list[str],
) -> str:
    """Infer an AI-oriented product category from repository metadata."""

    lowered_topics = [topic.strip().lower() for topic in topics if topic]
    text_blob = " ".join(
        [
            repo_full_name.lower(),
            description.lower(),
            primary_language.lower(),
            *lowered_topics,
        ]
    )
    scores: dict[str, int] = {}
    for category, keywords in _CATEGORY_KEYWORDS.items():
        score = 0
        for keyword in keywords:
            if keyword in lowered_topics:
                score += 3
            elif keyword in text_blob:
                score += 1
        if score > 0:
            scores[category] = score

    if not scores:
        return "Other"

    return max(scores.items(), key=lambda item: (item[1], item[0]))[0]


def load_repo_snapshots(
    *,
    parquet_base_path: str,
    days: int,
    include_previous_window: bool = False,
) -> list[dict[str, Any]]:
    """Build repository-level snapshots from Parquet event archives."""

    cache_key = (parquet_base_path, days, include_previous_window)
    cached = _read_cache(_snapshot_cache, _snapshot_cache_lock, cache_key)
    if cached is not None:
        return cached

    wait_event = _register_inflight(_snapshot_inflight, _snapshot_cache_lock, cache_key)
    if wait_event is not None:
        wait_event.wait(timeout=_CACHE_TTL.total_seconds())
        cached_after_wait = _read_cache(_snapshot_cache, _snapshot_cache_lock, cache_key)
        if cached_after_wait is not None:
            return cached_after_wait

    now = datetime.now(tz=UTC)
    current_cutoff = now - timedelta(days=days)
    previous_cutoff = now - timedelta(days=days * 2 if include_previous_window else days)
    repo_map: dict[str, dict[str, Any]] = {}
    try:
        for record, event_type, created_at in _iter_recent_records(
            parquet_base_path=parquet_base_path,
            cutoff=previous_cutoff,
            columns=[
                "actor_login",
                "repo_id",
                "repo_name",
                "created_at",
                "repo_stargazers_count",
                "repo_primary_language",
                "repo_topics",
                "repo_description",
                "repo_full_metadata_json",
            ],
            event_types={"WatchEvent"},
        ):
            repo_key = _repo_key(record)
            if repo_key is None:
                continue

            repo = repo_map.setdefault(repo_key, _new_repo_snapshot(repo_key))
            _merge_repo_metadata(repo, record, created_at)

            if created_at >= current_cutoff:
                repo["had_recent_event"] = True
                repo["total_events_in_window"] = int(repo["total_events_in_window"]) + 1
                if event_type == "WatchEvent":
                    repo["star_count_in_window"] = int(repo["star_count_in_window"]) + 1
                    actor_login = str(record.get("actor_login") or "").strip()
                    if actor_login:
                        repo["_actor_logins"].add(actor_login)
            elif include_previous_window and event_type == "WatchEvent":
                repo["previous_star_count_in_window"] = (
                    int(repo["previous_star_count_in_window"]) + 1
                )

        snapshots: list[dict[str, Any]] = []
        for repo in repo_map.values():
            repo["unique_actors_in_window"] = len(repo["_actor_logins"])
            repo.pop("_actor_logins", None)
            repo["category"] = infer_repo_category(
                repo_full_name=str(repo["repo_full_name"]),
                description=str(repo["description"]),
                primary_language=str(repo["primary_language"]),
                topics=list(repo["topics"]),
            )
            repo["star_delta"] = int(repo["star_count_in_window"])
            snapshots.append(repo)
        _write_cache(
            _snapshot_cache,
            _snapshot_cache_lock,
            _snapshot_inflight,
            cache_key,
            snapshots,
        )
        return deepcopy(snapshots)
    except Exception:
        _release_inflight(_snapshot_inflight, _snapshot_cache_lock, cache_key)
        raise


def load_repo_timeseries(
    *,
    parquet_base_path: str,
    repo_name: str,
    days: int,
) -> list[dict[str, Any]]:
    """Build a daily repository activity series from Parquet archives."""

    cache_key = (parquet_base_path, repo_name, days)
    cached = _read_cache(_timeseries_cache, _timeseries_cache_lock, cache_key)
    if cached is not None:
        return cached

    wait_event = _register_inflight(_timeseries_inflight, _timeseries_cache_lock, cache_key)
    if wait_event is not None:
        wait_event.wait(timeout=_CACHE_TTL.total_seconds())
        cached_after_wait = _read_cache(_timeseries_cache, _timeseries_cache_lock, cache_key)
        if cached_after_wait is not None:
            return cached_after_wait

    normalized_repo_name = repo_name.strip().lower()
    now = datetime.now(tz=UTC)
    cutoff = now - timedelta(days=days)
    points: dict[date, dict[str, Any]] = {}
    try:
        for record, event_type, created_at in _iter_recent_records(
            parquet_base_path=parquet_base_path,
            cutoff=cutoff,
            columns=["repo_name", "created_at"],
            event_types={"WatchEvent"},
        ):
            repo_key = _repo_key(record)
            if repo_key != normalized_repo_name:
                continue

            bucket = points.setdefault(
                created_at.date(),
                {
                    "event_date": created_at.date(),
                    "star_count": 0,
                    "total_events": 0,
                },
            )
            bucket["total_events"] = int(bucket["total_events"]) + 1
            if event_type == "WatchEvent":
                bucket["star_count"] = int(bucket["star_count"]) + 1

        result = [points[key] for key in sorted(points)]
        _write_cache(
            _timeseries_cache,
            _timeseries_cache_lock,
            _timeseries_inflight,
            cache_key,
            result,
        )
        return deepcopy(result)
    except Exception:
        _release_inflight(_timeseries_inflight, _timeseries_cache_lock, cache_key)
        raise


def prefer_ai_repositories(
    repos: list[dict[str, Any]],
    *,
    category: str | None = None,
) -> list[dict[str, Any]]:
    """Prefer AI-classified repositories for default product surfaces."""

    if category and category.strip():
        return [repo for repo in repos if str(repo["category"]) == category]

    ai_repos = [repo for repo in repos if str(repo["category"]) != "Other"]
    return ai_repos or repos


def _iter_recent_records(
    *,
    parquet_base_path: str,
    cutoff: datetime,
    columns: list[str] | None = None,
    event_types: set[str] | None = None,
) -> Iterator[tuple[dict[str, Any], str, datetime]]:
    base_path = Path(parquet_base_path)
    if not base_path.exists():
        return
    cutoff_date = cutoff.date()

    for parquet_file in sorted(base_path.rglob("*.parquet")):
        partition_date = _extract_partition_date(parquet_file)
        if partition_date is not None and partition_date < cutoff_date:
            continue

        event_type = _extract_partition_value(parquet_file, "event_type")
        if event_types is not None and event_type not in event_types:
            continue
        parquet_reader = pq.ParquetFile(str(parquet_file))
        for batch in parquet_reader.iter_batches(batch_size=1000, columns=columns):
            for record in batch.to_pylist():
                created_at = _coerce_datetime(record.get("created_at"))
                if created_at < cutoff:
                    continue
                yield record, event_type, created_at


def _repo_key(record: dict[str, Any]) -> str | None:
    repo_name = str(record.get("repo_name") or "").strip()
    if not repo_name:
        return None
    return repo_name.lower()


def _new_repo_snapshot(repo_key: str) -> dict[str, Any]:
    owner_login, _, repo_name = repo_key.partition("/")
    return {
        "repo_id": 0,
        "repo_full_name": repo_key,
        "repo_name": repo_name or repo_key,
        "html_url": f"https://github.com/{repo_key}",
        "description": "",
        "primary_language": "",
        "topics": [],
        "category": "Other",
        "stargazers_count": 0,
        "watchers_count": 0,
        "forks_count": 0,
        "open_issues_count": 0,
        "subscribers_count": 0,
        "owner_login": owner_login,
        "owner_avatar_url": "",
        "license_name": "",
        "github_created_at": datetime.now(tz=UTC),
        "github_pushed_at": datetime.fromtimestamp(0, tz=UTC),
        "rank": 0,
        "star_count_in_window": 0,
        "star_delta": 0,
        "previous_star_count_in_window": 0,
        "unique_actors_in_window": 0,
        "total_events_in_window": 0,
        "had_recent_event": False,
        "_actor_logins": set(),
    }


def _merge_repo_metadata(
    snapshot: dict[str, Any],
    record: dict[str, Any],
    created_at: datetime,
) -> None:
    metadata = _parse_full_metadata_json(record.get("repo_full_metadata_json"))
    repo_full_name = str(metadata.get("full_name") or record.get("repo_name") or "").strip()
    if repo_full_name:
        owner = metadata.get("owner")
        owner_login = ""
        owner_avatar_url = ""
        if isinstance(owner, dict):
            owner_login = str(owner.get("login") or "")
            owner_avatar_url = str(owner.get("avatar_url") or "")

        snapshot["repo_full_name"] = repo_full_name
        snapshot["repo_name"] = repo_full_name.split("/")[-1]
        snapshot["html_url"] = str(
            metadata.get("html_url") or snapshot["html_url"] or f"https://github.com/{repo_full_name}"
        )
        snapshot["owner_login"] = str(
            owner_login or snapshot["owner_login"] or repo_full_name.split("/")[0]
        )
        if owner_avatar_url:
            snapshot["owner_avatar_url"] = owner_avatar_url

    snapshot["repo_id"] = max(int(snapshot["repo_id"]), _coerce_int(record.get("repo_id")))
    snapshot["stargazers_count"] = max(
        int(snapshot["stargazers_count"]),
        _coerce_int(metadata.get("stargazers_count") or record.get("repo_stargazers_count")),
    )
    snapshot["watchers_count"] = max(
        int(snapshot["watchers_count"]),
        _coerce_int(metadata.get("watchers_count") or snapshot["stargazers_count"]),
    )
    snapshot["forks_count"] = max(
        int(snapshot["forks_count"]),
        _coerce_int(metadata.get("forks_count")),
    )
    snapshot["open_issues_count"] = max(
        int(snapshot["open_issues_count"]),
        _coerce_int(metadata.get("open_issues_count")),
    )
    snapshot["subscribers_count"] = max(
        int(snapshot["subscribers_count"]),
        _coerce_int(metadata.get("subscribers_count")),
    )
    license_info = metadata.get("license")
    if isinstance(license_info, dict):
        snapshot["license_name"] = str(license_info.get("name") or snapshot["license_name"])

    description = str(
        metadata.get("description") or record.get("repo_description") or snapshot["description"]
    ).strip()
    if description:
        snapshot["description"] = description

    primary_language = str(
        metadata.get("language")
        or record.get("repo_primary_language")
        or snapshot["primary_language"]
    ).strip()
    if primary_language:
        snapshot["primary_language"] = primary_language

    topics = _coerce_string_list(
        metadata.get("topics") or record.get("repo_topics") or snapshot["topics"]
    )
    if topics:
        snapshot["topics"] = topics

    metadata_created_at = _coerce_datetime(
        metadata.get("created_at") or record.get("created_at") or created_at
    )
    metadata_pushed_at = _coerce_datetime(
        metadata.get("pushed_at") or record.get("created_at") or created_at
    )
    snapshot["github_created_at"] = min(
        _coerce_datetime(snapshot["github_created_at"]),
        metadata_created_at,
    )
    snapshot["github_pushed_at"] = max(
        _coerce_datetime(snapshot["github_pushed_at"]),
        metadata_pushed_at,
    )


def _parse_full_metadata_json(value: object | None) -> dict[str, Any]:
    if not isinstance(value, str) or not value.strip():
        return {}
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _extract_partition_date(path: Path) -> date | None:
    raw_value = _extract_partition_value(path, "event_date")
    if not raw_value:
        return None
    try:
        return date.fromisoformat(raw_value)
    except ValueError:
        return None


def _extract_partition_value(path: Path, key: str) -> str:
    prefix = f"{key}="
    for part in path.parts:
        if part.startswith(prefix):
            return part.split("=", maxsplit=1)[1]
    return ""


def _coerce_datetime(value: object | None) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return datetime.now(tz=UTC)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    return datetime.now(tz=UTC)


def _coerce_int(value: object | None) -> int:
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


def _coerce_string_list(value: object | None) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, tuple):
        return [str(item) for item in value if str(item).strip()]
    return []


def _read_cache(
    cache: dict[tuple[Any, ...], tuple[datetime, list[dict[str, Any]]]],
    lock: Lock,
    key: tuple[Any, ...],
) -> list[dict[str, Any]] | None:
    with lock:
        cached = cache.get(key)
        if cached is None:
            return None
        cached_at, payload = cached
        if datetime.now(tz=UTC) - cached_at > _CACHE_TTL:
            cache.pop(key, None)
            return None
        return deepcopy(payload)


def _register_inflight(
    inflight: dict[tuple[Any, ...], Event],
    lock: Lock,
    key: tuple[Any, ...],
) -> Event | None:
    with lock:
        existing = inflight.get(key)
        if existing is not None:
            return existing
        inflight[key] = Event()
        return None


def _write_cache(
    cache: dict[tuple[Any, ...], tuple[datetime, list[dict[str, Any]]]],
    lock: Lock,
    inflight: dict[tuple[Any, ...], Event],
    key: tuple[Any, ...],
    payload: list[dict[str, Any]],
) -> None:
    with lock:
        cache[key] = (datetime.now(tz=UTC), deepcopy(payload))
        event = inflight.pop(key, None)
        if event is not None:
            event.set()


def _release_inflight(
    inflight: dict[tuple[Any, ...], Event],
    lock: Lock,
    key: tuple[Any, ...],
) -> None:
    with lock:
        event = inflight.pop(key, None)
        if event is not None:
            event.set()
