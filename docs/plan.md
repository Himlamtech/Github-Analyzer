# Implementation Plan

## 1. Objective

This plan turns the current cleaned repository into a deliverable project roadmap with execution order, detailed acceptance criteria, and the backend/API gaps that must be closed before the full product can be implemented.

The immediate goal is not to build every intelligence surface at once. The goal is to ship the project in controlled phases where each new frontend page is backed by a real data model, stable API contract, and verifiable backend flow.

## 2. Current state summary

### Implemented now

- GitHub ingestion pipeline exists: GitHub API -> Kafka -> Spark -> ClickHouse + Parquet.
- FastAPI exposes health and dashboard analytics routes.
- The new Vite/React frontend is the active frontend.
- `Overview` and `BreakoutDetector` already consume live backend data.
- `EcosystemRotation` can use live topic rotation data partially.

### Missing today

- No intelligence-specific backend contracts for `NewsImpact`.
- No framework-radar backend model for `CompetitiveRadar`.
- No weekly-brief backend model or editorial snapshot contract.
- Category logic is still too neutral for real AI ecosystem intelligence.
- Most advanced frontend metrics are still derived or curated rather than computed from named server-side models.

### Guiding rule

Each new product surface must be shipped in this order:

1. analytical model
2. storage/read model
3. application orchestration
4. API contract
5. frontend binding

## 3. Scope boundaries

### In scope

- stabilize frontend/backend integration
- ship the next intelligence features only when backed by real server-side contracts
- document exact implementation sequence and acceptance criteria

### Out of scope for the first delivery wave

- fine-tuned ML classification in the serving path
- fully automatic editorial generation
- raw event queries directly from the browser

## 4. Delivery phases

## Phase 0. Stabilize the serving path

### Goal

Make the current frontend/backend integration reliable, explicit, and production-safe enough for further feature work.

### Work items

1. Keep `ClickHouse` as the serving source of truth.
2. Keep `Parquet` as archive and backfill storage only.
3. Freeze the current live contracts used by the frontend.
4. Remove ambiguity between live pages and curated pages.
5. Ensure local and Docker frontend runtime both reflect the Vite frontend.

### Acceptance criteria

#### AC-0.1 Runtime contract stability

- `Overview` loads from live backend routes without frontend-side mock fallback for its core metrics.
- `BreakoutDetector` loads ranking and repository detail history from live backend routes.
- If the backend is unavailable, the frontend shows an explicit degraded state instead of silently pretending data is live.

#### AC-0.2 Serving-source clarity

- All active frontend live reads originate from FastAPI.
- FastAPI serving reads originate from ClickHouse only.
- No active frontend view depends on reading Parquet directly.

#### AC-0.3 Documentation clarity

- Docs clearly mark which views are `Live`, `Partial`, and `Curated`.
- Docs explicitly identify the current request map between frontend pages and backend routes.

## Phase 1. Ship real breakout intelligence

### Goal

Replace presentation-derived breakout metrics with named backend intelligence outputs.

### Proposed backend scope

- introduce a curated breakout scoring model
- expose breakout results via dedicated intelligence route
- preserve current dashboard routes only as compatibility or general analytics routes

### Work items

1. Define breakout scoring inputs.
2. Build a ClickHouse read model for breakout scores.
3. Add application orchestration for score refresh/build.
4. Expose a dedicated intelligence API for breakout results.
5. Rebind `BreakoutDetector` to the intelligence API.

### Proposed API

- `GET /intelligence/breakout`
- optional: `GET /intelligence/breakout/{repo_full_name}`

### Suggested response fields

- repository identity: `repo_id`, `repo_full_name`, `repo_name`, `owner_login`, `html_url`
- metadata: `description`, `primary_language`, `topics`, `category`
- score outputs: `breakout_score`, `durability_score`, `hype_risk_score`, `confidence_score`
- evidence fields: `star_gain_7d`, `unique_actors_7d`, `event_count_7d`, `star_gain_vs_prev_window`
- explanation fields: `explanation_trace`, `last_computed_at`

### Acceptance criteria

#### AC-1.1 Backend model validity

- Breakout scores are computed server-side from defined inputs.
- Each returned repo includes a named confidence field.
- Each returned repo includes a short explanation trace or evidence summary.

#### AC-1.2 API correctness

- `GET /intelligence/breakout` returns sorted breakout results with deterministic schema.
- Response remains stable when there is no data: empty list, not ad-hoc shape changes.
- Validation errors and backend read failures return clear non-200 responses.

#### AC-1.3 Frontend binding

- `BreakoutDetector` no longer infers durable momentum or hype from ad-hoc client logic for the primary intelligence card.
- The page can sort/filter/render on server-provided intelligence fields.

#### AC-1.4 Verification

- unit tests cover score mapping and response shaping
- integration tests cover ClickHouse reads for breakout data
- frontend type-check/build passes after rebinding

## Phase 2. Ship category-aware ecosystem rotation

### Goal

Move `EcosystemRotation` from generic topic rotation toward category-level intelligence that reflects real AI ecosystem segments.

### Proposed backend scope

- upgrade category taxonomy
- build category-level rotation mart
- expose category-level rotation endpoint

### Proposed API

- `GET /intelligence/rotation`

### Suggested response fields

- `category`
- `current_attention_score`
- `previous_attention_score`
- `attention_delta`
- `repo_count`
- `top_repos`
- `top_topics`
- `confidence_score`
- `rotation_drivers`
- `last_computed_at`

### Acceptance criteria

#### AC-2.1 Taxonomy usefulness

- Categories are more meaningful than the current neutral fallback.
- Rotation results reflect AI ecosystem segments, not only raw GitHub topic strings.

#### AC-2.2 Contract usefulness

- Response contains enough information to render category cards and sidebar rationale without client-side invention.
- At least one evidence field is returned for why a category is moving.

#### AC-2.3 Frontend fidelity

- `EcosystemRotation` can render category cards from live backend responses.
- The sidebar summary reflects backend evidence instead of static copy for the key movement section.

## Phase 3. Ship news-to-code impact tracking

### Goal

Turn `NewsImpact` into a real product feature backed by external-source ingestion and causality scoring.

### Missing dependency

The project currently does not have a trusted external news/launch ingestion layer.

### Proposed backend scope

1. ingest official launch/news events
2. link events to repos, models, frameworks, and topics
3. compute lag and impact curves against GitHub telemetry
4. expose a frontend-ready causality endpoint

### Proposed API

- `GET /intelligence/news-impact`
- optional: `GET /intelligence/news-impact/{event_id}`

### Suggested response fields

- event identity: `event_id`, `source`, `headline`, `published_at`, `provider`
- classification: `event_type`, `linked_entities`, `linked_categories`
- causality outputs: `causality_score`, `lag_hours`, `impact_summary`
- trend outputs: `impact_curve` with time/value points
- linked repos: `top_impacted_repos`
- narrative fields: `explanation_trace`, `last_computed_at`

### Acceptance criteria

#### AC-3.1 External-source integrity

- Every event shown in the UI comes from a defined external source.
- Duplicate or low-confidence external events are quarantined before serving.

#### AC-3.2 Causality usefulness

- Each news event has a lag value and impact score.
- Each impact graph is derived from backend data, not static mock points.

#### AC-3.3 Frontend replacement

- `NewsImpact` no longer depends on `NEWS_IMPACT_EVENTS` for its main timeline.
- Selecting an item loads server-backed causality and curve data.

## Phase 4. Ship competitive radar

### Goal

Back `CompetitiveRadar` with real framework-level metrics rather than curated coordinates.

### Proposed backend scope

- define framework entities
- map repositories into frameworks/ecosystems
- compute velocity, readiness proxies, and contributor energy server-side

### Proposed API

- `GET /intelligence/framework-radar`

### Suggested response fields

- `framework_id`, `framework_name`
- `velocity_score`
- `commercial_readiness_score`
- `contributor_energy_score`
- `market_footprint`
- `strategic_insight_summary`
- `warnings`
- `winners`
- `last_computed_at`

### Acceptance criteria

#### AC-4.1 Model definition

- Radar coordinates come from named backend metrics.
- Axis meaning is documented and stable.

#### AC-4.2 Frontend binding

- Selecting a framework in the radar reads real returned values.
- Sidebar winners/warnings can be sourced from backend outputs or backend-ready summaries.

## Phase 5. Ship weekly brief snapshots

### Goal

Provide a real backend-backed briefing snapshot while preserving editorial quality.

### Proposed backend scope

- create a periodic briefing snapshot
- aggregate top signals into a stable read model
- optionally support manual editorial curation on top of generated data

### Proposed API

- `GET /intelligence/weekly-brief/latest`
- optional: `GET /intelligence/weekly-brief/archive`

### Suggested response fields

- `brief_id`, `published_at`, `title`
- `pillars`
- `summary_chart_data`
- `evidence_spotlights`
- `regional_indicators`
- `disclaimer`

### Acceptance criteria

#### AC-5.1 Snapshot integrity

- The weekly brief is versioned or timestamped.
- The page shows when the snapshot was produced.

#### AC-5.2 Data support

- Visualizations and evidence blocks can be sourced from backend-provided snapshot fields.
- Manual editorial text remains possible without changing frontend code structure.

## 5. Cross-cutting platform work

### Stability and guardrails

These are not optional if the intelligence product expands.

1. Source freshness guard
2. External data quarantine
3. Backpressure and cost guard
4. Data quality regression watcher
5. Serving read-model protection

### Acceptance criteria

#### AC-G.1 Freshness visibility

- Backend exposes whether core sources are stale.
- Staleness can be surfaced in the frontend without extra interpretation.

#### AC-G.2 Serving protection

- Intelligence pages read from curated marts or curated snapshots, not raw full-table request-time scans.

#### AC-G.3 Failure isolation

- External-source failures do not silently poison live intelligence views.

## 6. Detailed API gap list

## Already sufficient now

These existing backend routes are enough for the current live surfaces:

- `GET /pipeline/status`
- `GET /events/latest`
- `GET /dashboard/top-repos`
- `GET /dashboard/trending`
- `GET /dashboard/topic-rotation`
- `GET /dashboard/repo-timeseries`

## Internal APIs still needed

To finish the project beyond the current live core, we need these new backend contracts:

1. `GET /intelligence/breakout`
2. `GET /intelligence/rotation`
3. `GET /intelligence/news-impact`
4. `GET /intelligence/framework-radar`
5. `GET /intelligence/weekly-brief/latest`

## External APIs or data sources still needed

These are the additional upstream sources you need to provide, approve, or choose before we can implement the remaining curated pages as real products:

1. Official launch/news source list
   - Example sources: OpenAI news, Anthropic news, Google AI blog, major framework release feeds
   - Needed for `NewsImpact`

2. Framework/entity registry source
   - A maintained mapping of repositories -> framework/model/provider/category
   - Needed for `CompetitiveRadar`, `Rotation`, and `NewsImpact`

3. Optional editorial source or manual curation path
   - Needed if `WeeklyBrief` should include human-reviewed text rather than only generated summaries

4. Optional repo catalog enrichment inputs
   - More complete repo metadata or curated repo sets if you want stronger category segmentation than current event-driven coverage

## 7. What you need to provide me next

To keep implementation moving without guessing, these are the concrete things I need from you:

### Required decisions

1. Confirm whether we should create a new `/intelligence/*` route family now.
2. Confirm whether `WeeklyBrief` should stay curated for a while or become backend-driven in this phase.
3. Confirm whether `CompetitiveRadar` should be based on frameworks, repo groups, or manually curated named entities.

### Required inputs for external-data features

1. The list of official news/launch sources you trust.
2. Any existing taxonomy of AI categories/frameworks/providers you already want to use.
3. Any preferred news API, RSS feeds, or dataset you already have access to.

## 8. Recommended implementation order

1. Phase 0: stabilize current serving path and keep docs honest.
2. Phase 1: breakout intelligence.
3. Phase 2: category-aware ecosystem rotation.
4. Phase 3: news-to-code impact tracking.
5. Phase 4: competitive radar.
6. Phase 5: weekly brief snapshot.

## 9. Definition of success

The project is in a healthy implementation state when:

- every live page has a named backend contract
- every high-level score comes from a documented backend model
- curated pages are clearly labeled until they become live
- frontend never invents critical product intelligence on its own
- docs remain the single source of truth for current and next-step implementation work
