-- ClickHouse DDL — GitHub AI Trend Analyzer
-- Executed automatically on first container start via docker-entrypoint-initdb.d/

-- Create database if not exists
CREATE DATABASE IF NOT EXISTS github_analyzer;

-- ── Table: github_data ───────────────────────────────────────────────────────
-- Single source of truth for events + repo metadata snapshot.
CREATE TABLE IF NOT EXISTS github_analyzer.github_data
(
    event_id     String,
    event_type   LowCardinality(String),
    actor_id     Int64,
    actor_login  String,
    repo_id      Int64,
    repo_name    String,
    created_at   DateTime('UTC'),
    payload_json String   DEFAULT '',
    repo_stargazers_count Int64 DEFAULT 0,
    repo_primary_language LowCardinality(String) DEFAULT '',
    repo_topics Array(String),
    repo_description String DEFAULT '',
    repo_full_metadata_json String DEFAULT '',
    repo_readme_text String DEFAULT '',
    repo_issues_json String DEFAULT '',
    ingested_at  DateTime('UTC') DEFAULT now()
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(created_at)
ORDER BY (repo_id, created_at)
SETTINGS index_granularity = 8192;

-- ── Table: repo_metadata ─────────────────────────────────────────────────────
-- Latest synced GitHub repository metadata used by dashboard/API queries.
CREATE TABLE IF NOT EXISTS github_analyzer.repo_metadata
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
    refreshed_at DateTime('UTC')
)
ENGINE = ReplacingMergeTree(refreshed_at)
PARTITION BY toYYYYMM(refreshed_at)
ORDER BY repo_full_name
SETTINGS index_granularity = 8192;

-- ── Table: repo_metadata_history ────────────────────────────────────────────
-- Append-only-ish audit log of repository metadata snapshots per fetch cycle.
-- Duplicate replays with the same repo/source/timestamp collapse on merge.
CREATE TABLE IF NOT EXISTS github_analyzer.repo_metadata_history
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
    snapshot_source LowCardinality(String),
    snapshot_key String
)
ENGINE = ReplacingMergeTree(snapshot_at)
PARTITION BY toYYYYMM(snapshot_at)
ORDER BY (repo_full_name, snapshot_source, snapshot_at, snapshot_key)
SETTINGS index_granularity = 8192;

-- ── Materialized View: github_data -> repo_metadata_history ─────────────────
-- Stores one repository observation per ingested GitHub event so request
-- history is preserved even before the scheduled metadata refresh runs.
CREATE MATERIALIZED VIEW IF NOT EXISTS github_analyzer.github_data_to_repo_metadata_history_mv
TO github_analyzer.repo_metadata_history
AS
SELECT
    repo_id,
    repo_name AS repo_full_name,
    if(position(repo_name, '/') > 0, splitByChar('/', repo_name)[2], repo_name) AS repo_name,
    '' AS node_id,
    toUInt8(0) AS private,
    concat('https://github.com/', repo_name) AS html_url,
    concat('https://github.com/', repo_name, '.git') AS clone_url,
    '' AS homepage,
    repo_stargazers_count AS stargazers_count,
    repo_stargazers_count AS watchers_count,
    toInt64(0) AS forks_count,
    toInt64(0) AS open_issues_count,
    toInt64(0) AS network_count,
    toInt64(0) AS subscribers_count,
    toInt64(0) AS size_kb,
    created_at AS github_created_at,
    created_at AS github_updated_at,
    created_at AS github_pushed_at,
    repo_primary_language AS primary_language,
    repo_topics AS topics,
    'public' AS visibility,
    'main' AS default_branch,
    repo_description AS description,
    'Other' AS category,
    toUInt8(0) AS is_fork,
    toUInt8(0) AS is_archived,
    toUInt8(0) AS is_disabled,
    toUInt8(1) AS has_issues,
    toUInt8(0) AS has_wiki,
    toUInt8(0) AS has_discussions,
    toUInt8(0) AS has_pages,
    toUInt8(1) AS allow_forking,
    toUInt8(0) AS is_template,
    if(position(repo_name, '/') > 0, splitByChar('/', repo_name)[1], '') AS owner_login,
    toInt64(0) AS owner_id,
    '' AS owner_type,
    '' AS owner_avatar_url,
    '' AS license_key,
    '' AS license_name,
    '' AS license_spdx_id,
    toInt32(0) AS rank,
    created_at AS fetched_at,
    created_at AS refreshed_at,
    created_at AS snapshot_at,
    'github_event' AS snapshot_source,
    event_id AS snapshot_key
FROM github_analyzer.github_data;

-- ── Table: repo_star_counts ──────────────────────────────────────────────────
-- Daily star deltas generated by the Spark batch aggregation job.
CREATE TABLE IF NOT EXISTS github_analyzer.repo_star_counts
(
    event_date Date,
    repo_name String,
    star_count Int64
)
ENGINE = SummingMergeTree()
PARTITION BY toYYYYMM(event_date)
ORDER BY (repo_name, event_date)
SETTINGS index_granularity = 8192;

-- ── Table: repo_activity_summary ─────────────────────────────────────────────
-- Weekly aggregate counts generated by the Spark batch aggregation job.
CREATE TABLE IF NOT EXISTS github_analyzer.repo_activity_summary
(
    repo_name String,
    event_type LowCardinality(String),
    event_count Int64,
    unique_actors Int64,
    first_seen_at DateTime('UTC'),
    last_seen_at DateTime('UTC'),
    computed_at DateTime('UTC')
)
ENGINE = ReplacingMergeTree(computed_at)
PARTITION BY toYYYYMM(computed_at)
ORDER BY (repo_name, event_type)
SETTINGS index_granularity = 8192;
