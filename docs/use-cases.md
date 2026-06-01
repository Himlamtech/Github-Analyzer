# Use Cases

## Operational use cases

1. Poll GitHub events continuously into Kafka.
2. Process event streams into ClickHouse and Parquet.
3. Check pipeline health and freshness from FastAPI.

## Product use cases

1. View current top repositories by recent star activity.
2. View trending repositories over the current analytical window.
3. Inspect topic rotation to see where attention is moving.
4. Open a repository detail overlay and load its recent time series.

## Prioritized next use cases

### Intelligence use cases

1. Breakout detector with real confidence and durability scoring.
2. Ecosystem rotation by meaningful AI category, not neutral fallback labels.
3. Adoption lag after model launch.
4. News-to-code impact tracking backed by external-source ingestion.
5. Competitive radar for frameworks once scoring inputs are real.

### Stability and guardrail use cases

1. Source freshness guard.
2. External data quarantine.
3. Backpressure and cost guard.
4. Data quality regression watcher.
5. Serving read-model protection.

### External data control use cases

1. Model catalog sync.
2. Official launch and news sync.
3. Entity linking and taxonomy building.

## Delivery rule

New product use cases should ship in this order:

1. analytical model
2. storage/read model
3. application orchestration
4. API contract
5. frontend binding

## Current non-goals

- fully dynamic news causality engine in the frontend
- full backend support for every curated research panel
- replacing the current editorial/research copy with generated live content
