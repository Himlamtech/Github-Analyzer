# Phase 1 Technical Design: Breakout Detector and Ecosystem Rotation

## 1. Overview

Tai lieu nay cu the hoa `Phase 1` tu [docs/ai_usecase_research.md](/home/iec/lamnh/github/docs/ai_usecase_research.md:1)
thanh mot thiet ke ky thuat co the implement duoc ngay trong repo hien tai.

Scope cua `Phase 1`:

- `AI Repo Breakout Detector`
- `Ecosystem Rotation Map`
- curated marts phuc vu 2 use case nay
- API contracts phuc vu frontend moi
- migration path khoi route/fallback cu

Khong nam trong scope `Phase 1`:

- external model/news ingestion
- adoption lag
- news-to-code impact
- embedding-based entity linking

## 2. Current State

### Implemented now

- Raw event ingestion: `GitHub Events API -> Kafka -> Spark -> ClickHouse + Parquet`
- Dashboard query surface hien co:
  - `trending`
  - `shock movers`
  - `topic rotation`
- Dashboard service hien tai nam tap trung trong
  [src/infrastructure/storage/clickhouse_dashboard_service.py](/home/iec/lamnh/github/src/infrastructure/storage/clickhouse_dashboard_service.py:1)

### Important code-backed limitations

#### Category classifier hien tai chua phuc vu san pham intelligence

`CategoryClassifier` hien dang tra ve duy nhat `RepoCategory.OTHER` cho moi repo trong
[src/domain/services/category_classifier.py](/home/iec/lamnh/github/src/domain/services/category_classifier.py:1).

He qua:

- khong the build `ecosystem rotation` dung nghia category-level
- khong the tao `durability by category` co y nghia
- page frontend moi se bi ngheo signal neu khong nang cap classifier

#### Trending va topic rotation hien la endpoint analytics, chua phai intelligence mart

- `get_trending()` hien xep hang theo star activity cua tuan hien tai
- `get_topic_rotation()` hien so sanh current/prior window o muc topic raw
- logic hien dang query/fallback truc tiep tu raw va parquet

He qua:

- response phu thuoc vao runtime query logic thay vi bang tong hop on dinh
- frontend moi se kho co `confidence`, `durability`, `false hype risk`

## 3. Target State

`Phase 1` se them mot lop curated mart giua raw facts va serving API:

```mermaid
flowchart LR
    A[github_data raw facts] --> B[Phase 1 feature builders]
    C[repo_metadata] --> B
    D[category taxonomy v1] --> B
    B --> E[breakout_repo_scores]
    B --> F[ecosystem_rotation_daily]
    E --> G[/intelligence/breakout]
    F --> H[/intelligence/rotation]
```

Nguyen tac:

- frontend doc curated mart
- API khong tinh score lon tai request time
- category phai duoc nang cap toi thieu len rule-based `v1`

## 4. Phase 1 Deliverables

### Required

- `breakout_repo_scores` mart
- `ecosystem_rotation_daily` mart
- `CategoryClassifier v1` theo taxonomy AI
- 2 application use case build feature marts
- 2 endpoint intelligence dau tien

### Optional but recommended

- `breakout_repo_score_explanations` field dang JSON de frontend hien evidence chips
- `rotation_drivers` field dang JSON de frontend hien top repo/category movers

## 5. Taxonomy V1

### Target categories

`Phase 1` khong nen de classifier tiep tuc tra `Other` cho tat ca. Taxonomy `v1` nen gom:

- `coding_agents`
- `browser_computer_use`
- `rag`
- `eval_tooling`
- `inference_serving`
- `multimodal`
- `voice_audio`
- `video_generation`
- `safety_guardrails`
- `ai_infra_platform`
- `other_ai`
- `other`

### Classification strategy v1

Pha dau dung rule-based deterministic classifier:

- match theo `topics`
- match theo `description`
- uu tien keyword co precision cao
- fallback `other_ai` neu repo co dau hieu AI chung nhung khong vao category cu the
- fallback `other` neu khong co du signal

### Why rule-based first

- de test
- de explain
- de patch nhanh khi frontend can category moi
- khong tang chi phi van hanh som

## 6. Data Mart Design

### 6.1 breakout_repo_scores

Muc dich:

- phuc vu page `Breakout Detector`
- phuc vu card `Breakout Now`, `Durable Momentum`, `False Hype Risk` o dashboard

Grain:

- `1 row / repo / build_window / snapshot_time`

Suggested columns:

| Column | Type | Meaning |
|---|---|---|
| `snapshot_at` | `DateTime` | thoi diem build mart |
| `window_hours` | `UInt16` | cua so scoring, vi du 24, 72, 168 |
| `repo_id` | `UInt64` | id repo |
| `repo_full_name` | `String` | owner/repo |
| `category` | `LowCardinality(String)` | category taxonomy v1 |
| `primary_language` | `LowCardinality(String)` | ngon ngu chinh |
| `watch_events_24h` | `UInt32` | star events 24h |
| `watch_events_72h` | `UInt32` | star events 72h |
| `watch_events_7d` | `UInt32` | star events 7d |
| `fork_events_7d` | `UInt32` | fork events 7d |
| `push_events_7d` | `UInt32` | push events 7d |
| `issues_events_7d` | `UInt32` | issues events 7d |
| `unique_actors_7d` | `UInt32` | unique actors 7d |
| `active_days_14d` | `UInt16` | so ngay co activity |
| `baseline_stars` | `UInt32` | tong stars tu metadata |
| `breakout_score` | `Float32` | score tong hop |
| `durability_score` | `Float32` | score do ben |
| `false_hype_risk` | `Float32` | score rui ro hype |
| `confidence_score` | `Float32` | muc do tin cay cua score |
| `evidence_json` | `String` | serialized evidence cho UI |
| `build_version` | `String` | version scoring, vi du `breakout_v1` |

Partitioning suggestion:

- partition theo `toDate(snapshot_at)`
- order by `(window_hours, category, breakout_score, repo_id)`

Retention suggestion:

- giu `90-180 ngay` cho mart online
- co the archive lau hon neu can historical comparisons

### 6.2 ecosystem_rotation_daily

Muc dich:

- phuc vu page `Ecosystem Rotation`
- phuc vu card `Rotation Into` va `Frameworks Losing Momentum`

Grain:

- `1 row / category / snapshot_date / comparison_window`

Suggested columns:

| Column | Type | Meaning |
|---|---|---|
| `snapshot_date` | `Date` | ngay tong hop |
| `window_days` | `UInt16` | cua so tinh, vi du 7 |
| `category` | `LowCardinality(String)` | category duoc do |
| `current_watch_events` | `UInt32` | star events current window |
| `previous_watch_events` | `UInt32` | star events prior window |
| `current_active_repos` | `UInt32` | repo active current window |
| `previous_active_repos` | `UInt32` | repo active previous window |
| `current_unique_actors` | `UInt32` | actor hien tai |
| `previous_unique_actors` | `UInt32` | actor truoc do |
| `rotation_score` | `Float32` | muc do tang/roi attention |
| `durability_score` | `Float32` | do ben category |
| `confidence_score` | `Float32` | do tin cay do category coverage |
| `top_rising_repos_json` | `String` | danh sach repo keo category len |
| `top_falling_repos_json` | `String` | danh sach repo giam dong luc |
| `build_version` | `String` | version scoring |

Partitioning suggestion:

- partition theo `snapshot_date`
- order by `(window_days, rotation_score, category)`

## 7. Scoring Formula V1

### 7.1 Breakout score v1

Muc tieu:

- uu tien repo dang tang nhanh
- khong de repo qua lon luon thang chi vi baseline cao
- tach momentum that is real voi one-off noise

Suggested normalized components:

- `watch_velocity_component`
- `fork_velocity_component`
- `push_continuity_component`
- `issues_intensity_component`
- `unique_actor_component`
- `novelty_component`

Cong thuc goi y:

```text
breakout_score_v1 =
  0.35 * normalized_watch_velocity
  + 0.20 * normalized_fork_velocity
  + 0.15 * normalized_push_continuity
  + 0.10 * normalized_issue_intensity
  + 0.10 * normalized_unique_actors
  + 0.10 * normalized_novelty
```

Trong do:

- `normalized_watch_velocity` uu tien 24h va 72h hon 7d
- `normalized_novelty` co the don gian la repo moi xuat hien trong tap theo doi hoac topic AI moi

### 7.2 Durability score v1

Cong thuc goi y:

```text
durability_score_v1 =
  0.45 * normalized_active_days_14d
  + 0.25 * normalized_push_continuity
  + 0.20 * normalized_unique_actors
  + 0.10 * normalized_repeat_watch_distribution
```

### 7.3 False hype risk v1

False hype risk phai cao khi:

- stars tang manh nhung push/issue continuity thap
- actor concentration qua it
- category evidence yeu

Cong thuc goi y:

```text
false_hype_risk_v1 =
  0.50 * spike_without_followthrough
  + 0.30 * low_actor_diversity
  + 0.20 * weak_repo_activity_mix
```

### 7.4 Confidence score v1

Confidence score khong do momentum, ma do tin cay cua score.

Tang khi:

- repo co metadata day du
- category classify duoc khong roi vao `other`
- event mix khong bi mat key fields
- co du so diem du lieu trong cua so tinh

## 8. Build Jobs

### Application use cases de them

- `build_breakout_rankings.py`
- `build_ecosystem_rotation.py`

### Runtime cadence de xuat

- `breakout_repo_scores`: moi `15 phut`
- `ecosystem_rotation_daily`: moi `1 gio` hoac `15 phut` voi snapshot rolling 7d

### Input sources

- `github_data`
- `repo_metadata`
- taxonomy config/rules

### Output guarantee

- build idempotent
- co `build_version`
- ghi snapshot moi thay vi update ngau nhien tren cung row

## 9. API Contract Proposal

### 9.1 `GET /intelligence/breakout`

Query params:

- `window_hours`: `24 | 72 | 168`
- `category`: optional
- `limit`: default `20`, max `100`
- `sort_by`: `breakout_score | durability_score | false_hype_risk`

Response shape:

```json
{
  "snapshot_at": "2026-06-01T09:00:00Z",
  "window_hours": 72,
  "build_version": "breakout_v1",
  "items": [
    {
      "repo_id": 123,
      "repo_full_name": "org/repo",
      "category": "coding_agents",
      "primary_language": "Python",
      "baseline_stars": 4200,
      "breakout_score": 0.91,
      "durability_score": 0.74,
      "false_hype_risk": 0.18,
      "confidence_score": 0.88,
      "watch_events_24h": 320,
      "watch_events_72h": 910,
      "fork_events_7d": 140,
      "push_events_7d": 96,
      "unique_actors_7d": 502,
      "evidence": [
        "watch velocity accelerated 2.4x vs prior window",
        "active on 11 of last 14 days"
      ]
    }
  ]
}
```

### 9.2 `GET /intelligence/rotation`

Query params:

- `window_days`: default `7`
- `limit`: default `12`
- `direction`: `rising | falling | all`

Response shape:

```json
{
  "snapshot_date": "2026-06-01",
  "window_days": 7,
  "build_version": "rotation_v1",
  "items": [
    {
      "category": "browser_computer_use",
      "current_watch_events": 3400,
      "previous_watch_events": 1800,
      "current_active_repos": 46,
      "previous_active_repos": 23,
      "rotation_score": 0.86,
      "durability_score": 0.69,
      "confidence_score": 0.81,
      "top_rising_repos": ["org/a", "org/b"],
      "top_falling_repos": []
    }
  ]
}
```

## 10. Migration Plan

### Current -> target mapping

| Current endpoint/logic | Target replacement | Migration note |
|---|---|---|
| `/dashboard/trending` | `/intelligence/breakout` | `trending` co the giu tam thoi cho backward compatibility |
| `/dashboard/topic-rotation` | `/intelligence/rotation` | `topic` raw se duoc thay bang `category` rotation |
| fallback to parquet in dashboard service | curated marts in ClickHouse | bo dan sau khi Phase 1 on dinh |
| neutral `CategoryClassifier` | rule-based taxonomy v1 | bat buoc de page rotation co gia tri |

### Recommended rollout

1. Build marts trong ClickHouse nhung chua expose frontend.
2. Add intelligence endpoints moi song song voi dashboard endpoints cu.
3. Frontend moi bind vao endpoint moi.
4. Theo doi latency, freshness, va quality.
5. Sau khi on dinh, mark route cu la deprecated.

## 11. File Impact

| Path | Action | Brief change | Why |
|---|---|---|---|
| `src/domain/services/category_classifier.py` | Modify | Nang cap classifier tu neutral fallback sang taxonomy v1 | Phase 1 khong the thanh cong neu category van la `Other` |
| `src/application/use_cases/` | Add | Them use case build breakout va rotation | Tach orchestration khoi presentation va storage |
| `src/infrastructure/storage/` | Add/Modify | Them mart repository/query service cho breakout va rotation | Serving doc curated data |
| `src/presentation/api/` | Modify | Them intelligence routes moi | Phuc vu frontend moi ma khong pha route cu ngay |
| `tests/` | Add/Modify | Them regression tests cho taxonomy, scoring, API contracts | Bao ve rollout |

## 12. Testing And Verification

### Unit

- classifier topic/description mapping
- breakout scoring formula v1
- durability/risk/confidence calculations

### Integration

- build mart tu fixture `github_data + repo_metadata`
- endpoint `/intelligence/breakout`
- endpoint `/intelligence/rotation`

### Performance

- benchmark build time voi 10M records fixture
- benchmark endpoint latency tren curated mart

### Negative paths

- repo metadata thieu topics/description
- category classifier roi ve `other` qua nguong canh bao
- gold mart snapshot cu hon freshness SLA

## 13. Definition Of Done

- `CategoryClassifier v1` phan loai duoc phan lon repo AI ve category co y nghia.
- `breakout_repo_scores` va `ecosystem_rotation_daily` duoc build theo cadence da chot.
- frontend co the bind vao 2 endpoint moi ma khong can query raw dashboard endpoints.
- p95 query cho intelligence endpoints dat SLA da de xuat.
- co observability cho build freshness, build failures, va category coverage.

## 14. Recommended Next Step

PR implementation dau tien nen tap trung duy nhat vao:

1. `CategoryClassifier v1`
2. schema + builder cho `breakout_repo_scores`
3. `/intelligence/breakout`

Sau khi breakout page on dinh, moi mo rong sang `ecosystem_rotation_daily`.
