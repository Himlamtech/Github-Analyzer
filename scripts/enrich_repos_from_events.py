"""One-shot script: fetch GitHub API metadata for the top-active repos in
github_data and upsert them into repo_metadata. Also backfills
repo_star_counts from WatchEvents already in github_data.

Usage:
    python scripts/enrich_repos_from_events.py [--limit N]

Requires:
    - GITHUB_API_TOKENS in .env
    - ClickHouse accessible on localhost:9000
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import UTC, datetime
import os
from pathlib import Path
import sys

from clickhouse_driver import Client
from dotenv import load_dotenv
import httpx
import structlog

# ── Bootstrap ──────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")

log = structlog.get_logger(__name__)
JsonObject = dict[str, object]

_CREATE_HISTORY_TABLE_QUERY = """
CREATE TABLE IF NOT EXISTS repo_metadata_history
(
    repo_id Int64,
    repo_full_name String,
    repo_name String,
    node_id String,
    private UInt8,
    html_url String,
    clone_url String,
    homepage String,
    stargazers_count Int64,
    watchers_count Int64,
    forks_count Int64,
    open_issues_count Int64,
    network_count Int64,
    subscribers_count Int64,
    size_kb Int64,
    github_created_at DateTime('UTC'),
    github_updated_at DateTime('UTC'),
    github_pushed_at DateTime('UTC'),
    primary_language LowCardinality(String),
    topics Array(String),
    visibility LowCardinality(String),
    default_branch String,
    description String,
    category LowCardinality(String),
    is_fork UInt8,
    is_archived UInt8,
    is_disabled UInt8,
    has_issues UInt8,
    has_wiki UInt8,
    has_discussions UInt8,
    has_pages UInt8,
    allow_forking UInt8,
    is_template UInt8,
    owner_login String,
    owner_id Int64,
    owner_type LowCardinality(String),
    owner_avatar_url String,
    license_key String,
    license_name String,
    license_spdx_id String,
    rank Int32,
    fetched_at DateTime('UTC'),
    refreshed_at DateTime('UTC'),
    snapshot_at DateTime('UTC'),
    snapshot_source LowCardinality(String)
)
ENGINE = ReplacingMergeTree(snapshot_at)
PARTITION BY toYYYYMM(snapshot_at)
ORDER BY (repo_full_name, snapshot_source, snapshot_at)
SETTINGS index_granularity = 8192
"""

# ── Config ─────────────────────────────────────────────────────────────────
TOKENS = [t.strip() for t in os.getenv("GITHUB_API_TOKENS", "").split(",") if t.strip()]
CH_HOST = os.getenv("CLICKHOUSE_HOST", "localhost")
CH_PORT = int(os.getenv("CLICKHOUSE_PORT", "9000"))
CH_USER = os.getenv("CLICKHOUSE_USER", "analyst")
CH_PASS = os.getenv("CLICKHOUSE_PASSWORD", "analyst_password")
CH_DB = os.getenv("CLICKHOUSE_DATABASE", "github_analyzer")

# Category classification rules (simple keyword matching on topics/description)
_CATEGORY_RULES: list[tuple[set[str], str]] = [
    (
        {
            "llm",
            "gpt",
            "chatgpt",
            "language-model",
            "language model",
            "transformer",
            "bert",
            "t5",
            "llama",
            "mistral",
            "gemma",
            "phi",
            "falcon",
            "alpaca",
        },
        "LLM",
    ),
    (
        {
            "agent",
            "rag",
            "retrieval",
            "langchain",
            "langgraph",
            "crewai",
            "autogen",
            "multi-agent",
            "autonomous",
            "tool-calling",
        },
        "Agent",
    ),
    (
        {
            "diffusion",
            "stable-diffusion",
            "image-generation",
            "text-to-image",
            "midjourney",
            "dall-e",
            "flux",
            "comfyui",
            "inpainting",
        },
        "Diffusion",
    ),
    (
        {
            "multimodal",
            "vision",
            "vqa",
            "clip",
            "image-text",
            "video",
            "speech",
            "audio",
            "whisper",
            "tts",
            "asr",
        },
        "Multimodal",
    ),
    (
        {
            "embedding",
            "vector",
            "qdrant",
            "milvus",
            "faiss",
            "pinecone",
            "data",
            "etl",
            "pipeline",
            "spark",
            "kafka",
            "dbt",
        },
        "DataEng",
    ),
]


def classify_category(topics: list[str], description: str, repo_name: str) -> str:
    haystack = " ".join(topics).lower() + " " + description.lower() + " " + repo_name.lower()
    for keywords, category in _CATEGORY_RULES:
        if any(kw in haystack for kw in keywords):
            return category
    return "Other"


def get_clickhouse_client() -> Client:
    return Client(
        host=CH_HOST,
        port=CH_PORT,
        user=CH_USER,
        password=CH_PASS,
        database=CH_DB,
    )


def get_top_repos(client: Client, limit: int) -> list[str]:
    """Return repo names most active in github_data."""
    rows = client.execute(
        """
        SELECT repo_name, count() AS n
        FROM github_data
        WHERE created_at >= now() - INTERVAL 30 DAY
        GROUP BY repo_name
        ORDER BY n DESC
        LIMIT %(limit)s
        """,
        {"limit": limit},
    )
    return [str(r[0]) for r in rows]


def get_known_repos(client: Client) -> set[str]:
    """Return repo_full_names already in repo_metadata."""
    rows = client.execute("SELECT repo_full_name FROM repo_metadata FINAL")
    return {str(r[0]) for r in rows}


def _as_json_object(value: object) -> JsonObject:
    if not isinstance(value, dict):
        return {}
    return {str(key): item for key, item in value.items()}


def _as_string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if item]


async def fetch_github_metadata(
    http: httpx.AsyncClient, token: str, repo_full_name: str
) -> JsonObject | None:
    try:
        resp = await http.get(
            f"https://api.github.com/repos/{repo_full_name}",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=15.0,
        )
        if resp.status_code == 200:
            payload = resp.json()
            if isinstance(payload, dict):
                return _as_json_object(payload)
            log.warning("github_fetch_invalid_payload", repo=repo_full_name)
            return None
        log.warning("github_fetch_failed", repo=repo_full_name, status=resp.status_code)
    except (httpx.HTTPError, ValueError) as exc:
        log.warning("github_fetch_error", repo=repo_full_name, error=str(exc))
    return None


def _parse_dt(s: str | None) -> datetime:
    if not s:
        return datetime(1970, 1, 1, tzinfo=UTC)
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return datetime(1970, 1, 1, tzinfo=UTC)


def ensure_history_table(client: Client) -> None:
    """Create the repo metadata history table when the stack predates this feature."""
    client.execute(_CREATE_HISTORY_TABLE_QUERY)


def upsert_repo_metadata(
    client: Client,
    meta: JsonObject,
    *,
    snapshot_source: str,
) -> None:
    now = datetime.now(UTC)
    topics = _as_string_list(meta.get("topics"))

    description = str(meta.get("description") or "")
    repo_name_short = str(meta.get("name") or "")
    repo_full_name = str(meta.get("full_name") or "")
    category = classify_category(topics, description, repo_full_name)

    owner = _as_json_object(meta.get("owner"))
    license_info = _as_json_object(meta.get("license"))

    row = (
        int(meta.get("id") or 0),
        repo_full_name,
        repo_name_short,
        str(meta.get("node_id") or ""),
        1 if meta.get("private") else 0,
        str(meta.get("html_url") or ""),
        str(meta.get("clone_url") or ""),
        str(meta.get("homepage") or ""),
        int(meta.get("stargazers_count") or 0),
        int(meta.get("watchers_count") or 0),
        int(meta.get("forks_count") or 0),
        int(meta.get("open_issues_count") or 0),
        int(meta.get("network_count") or 0),
        int(meta.get("subscribers_count") or 0),
        int(meta.get("size") or 0),
        _parse_dt(meta.get("created_at")),
        _parse_dt(meta.get("updated_at")),
        _parse_dt(meta.get("pushed_at")),
        str(meta.get("language") or ""),
        topics,
        str(meta.get("visibility") or "public"),
        str(meta.get("default_branch") or "main"),
        description,
        category,
        1 if meta.get("fork") else 0,
        1 if meta.get("archived") else 0,
        1 if meta.get("disabled") else 0,
        1 if meta.get("has_issues") else 0,
        1 if meta.get("has_wiki") else 0,
        1 if meta.get("has_discussions") else 0,
        1 if meta.get("has_pages") else 0,
        1 if meta.get("allow_forking") else 0,
        1 if meta.get("is_template") else 0,
        str(owner.get("login") or ""),
        int(owner.get("id") or 0),
        str(owner.get("type") or ""),
        str(owner.get("avatar_url") or ""),
        str(license_info.get("key") or ""),
        str(license_info.get("name") or ""),
        str(license_info.get("spdx_id") or ""),
        0,
        now,
        now,
    )

    client.execute(
        """
        INSERT INTO repo_metadata (
            repo_id, repo_full_name, repo_name, node_id, private, html_url,
            clone_url, homepage, stargazers_count, watchers_count, forks_count,
            open_issues_count, network_count, subscribers_count, size_kb,
            github_created_at, github_updated_at, github_pushed_at,
            primary_language, topics, visibility, default_branch, description,
            category, is_fork, is_archived, is_disabled, has_issues, has_wiki,
            has_discussions, has_pages, allow_forking, is_template,
            owner_login, owner_id, owner_type, owner_avatar_url,
            license_key, license_name, license_spdx_id,
            rank, fetched_at, refreshed_at
        ) VALUES
        """,
        [row],
    )
    client.execute(
        """
        INSERT INTO repo_metadata_history (
            repo_id, repo_full_name, repo_name, node_id, private, html_url,
            clone_url, homepage, stargazers_count, watchers_count, forks_count,
            open_issues_count, network_count, subscribers_count, size_kb,
            github_created_at, github_updated_at, github_pushed_at,
            primary_language, topics, visibility, default_branch, description,
            category, is_fork, is_archived, is_disabled, has_issues, has_wiki,
            has_discussions, has_pages, allow_forking, is_template,
            owner_login, owner_id, owner_type, owner_avatar_url,
            license_key, license_name, license_spdx_id,
            rank, fetched_at, refreshed_at, snapshot_at, snapshot_source
        ) VALUES
        """,
        [(*row, now, snapshot_source)],
    )
    log.info(
        "repo_upserted",
        repo=repo_full_name,
        stars=int(meta.get("stargazers_count") or 0),
        category=category,
    )


def backfill_repo_star_counts(client: Client) -> None:
    """Insert a row into repo_star_counts for each day with WatchEvents.

    Schema: repo_name (String), event_date (Date), star_count (Int64).
    """
    rows = client.execute(
        """
        SELECT
            repo_name,
            toDate(created_at)                   AS event_date,
            countIf(event_type = 'WatchEvent')   AS star_count
        FROM github_data
        GROUP BY repo_name, event_date
        HAVING star_count > 0
        """
    )
    if not rows:
        log.info("no_watch_events_found_for_backfill")
        return

    insert_rows = [
        (str(repo_name), event_date, int(star_count)) for repo_name, event_date, star_count in rows
    ]

    client.execute(
        "INSERT INTO repo_star_counts (repo_name, event_date, star_count) VALUES",
        insert_rows,
    )
    log.info("backfilled_star_counts", rows=len(insert_rows))


async def main(limit: int) -> None:
    if not TOKENS:
        log.error("no_github_tokens", hint="Set GITHUB_API_TOKENS in .env")
        sys.exit(1)

    client = get_clickhouse_client()
    ensure_history_table(client)

    log.info("fetching_top_active_repos", limit=limit)
    top_repos = get_top_repos(client, limit)
    known_repos = get_known_repos(client)

    to_fetch = [r for r in top_repos if r not in known_repos]
    log.info(
        "repos_to_enrich",
        total=len(top_repos),
        already_known=len(known_repos),
        to_fetch=len(to_fetch),
    )

    # Backfill repo_star_counts from WatchEvents
    backfill_repo_star_counts(client)

    if not to_fetch:
        log.info("all_repos_already_in_metadata")
        return

    token_cycle = iter(TOKENS * ((len(to_fetch) // len(TOKENS)) + 2))

    async with httpx.AsyncClient() as http:
        # Process in batches of 10 (rate-limit friendly)
        batch_size = 10
        enriched = 0
        failed = 0

        for i in range(0, len(to_fetch), batch_size):
            batch = to_fetch[i : i + batch_size]
            token = next(token_cycle)

            tasks = [fetch_github_metadata(http, token, repo) for repo in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for repo, result in zip(batch, results, strict=False):
                if isinstance(result, dict) and result:
                    upsert_repo_metadata(
                        client,
                        result,
                        snapshot_source="enrich_repos_from_events",
                    )
                    enriched += 1
                else:
                    log.warning("skipped_repo", repo=repo)
                    failed += 1

            # Be gentle with rate limits
            if i + batch_size < len(to_fetch):
                await asyncio.sleep(1.0)

    log.info("enrichment_done", enriched=enriched, failed=failed)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Enrich repo_metadata from github_data")
    parser.add_argument(
        "--limit", type=int, default=100, help="Max repos to enrich (default: 100)"
    )
    args = parser.parse_args()
    asyncio.run(main(args.limit))
