# Database

## ClickHouse

ClickHouse is the serving database for dashboard analytics.

Current responsibilities:

- serve live dashboard queries
- provide latest-event reads
- support time-series queries for breakout repository detail views
- persist official external news items for `NewsImpact`
- persist source health snapshots for external news sync observability

## Parquet

Parquet remains the archival and backfill store.

Current responsibilities:

- preserve raw event history
- support backfill into ClickHouse when needed
- act as the durable batch-oriented sink for the streaming job

## Practical split

- frontend never reads Parquet directly
- FastAPI dashboard endpoints read from ClickHouse
- operational backfill scripts can read Parquet and repopulate ClickHouse

## Recommended next storage layer

If the intelligence product grows, add curated marts in ClickHouse rather than serving new pages from raw fact scans.

Likely marts:

- `breakout_repo_scores`
- `ecosystem_rotation_daily`
- `source_health_snapshots`
- `external_news_items`

These marts should exist before high-level pages such as breakout confidence, durable momentum, false-hype risk, or framework radar become fully live.
