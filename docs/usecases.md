# Use Cases của GitHub Analyzer

> Tài liệu này được viết để hỗ trợ làm slide báo cáo bằng tiếng Việt. Mục tiêu không chỉ liệt kê tính năng, mà còn giải thích **ai dùng**, **dùng để làm gì**, **luồng hoạt động**, **dữ liệu đi qua hệ thống như thế nào**, và **mức độ hoàn thiện hiện tại** của từng use case.

## 1. Tóm tắt sản phẩm

**GitHub Analyzer** là một hệ thống phân tích telemetry GitHub gần thời gian thực. Hệ thống thu thập GitHub Events, xử lý qua pipeline dữ liệu lớn, lưu vào ClickHouse/Parquet, rồi cung cấp API analytics cho dashboard React.

Nói ngắn gọn:

- GitHub là nguồn phát sinh dữ liệu hành vi của cộng đồng developer.
- Pipeline ingest và xử lý các event đó.
- Backend biến dữ liệu thô thành các góc nhìn analytics/intelligence.
- Frontend giúp người dùng xem repo nào đang nổi, ecosystem nào đang dịch chuyển, tin tức bên ngoài có tác động gì tới GitHub, framework nào có momentum tốt.

## 2. Bức tranh kiến trúc tổng quan

```text
GitHub Events API
  -> PollGithubEventsUseCase
  -> Kafka
  -> Spark Structured Streaming
  -> ClickHouse + Parquet
  -> FastAPI dashboard/intelligence endpoints
  -> Vite/React frontend
```

### 2.1 Vai trò từng tầng

| Tầng | Vai trò | Ví dụ trong dự án |
| --- | --- | --- |
| `domain` | Mô hình nghiệp vụ thuần: event, metadata, category, value objects, repository contracts | `src/domain/entities`, `src/domain/repositories` |
| `application` | Use case orchestration: điều phối nghiệp vụ, tính snapshot, gọi repository/service | `src/application/use_cases` |
| `infrastructure` | Kết nối công nghệ cụ thể: GitHub API, Kafka, Spark, ClickHouse, Parquet, RSS | `src/infrastructure` |
| `presentation` | FastAPI routes, nhận request và trả response | `src/presentation/api` |
| `frontend` | Dashboard UI, gọi API và trình bày insight | `frontend/src` |

### 2.2 Luồng dữ liệu cấp cao

1. **Ingestion:** hệ thống poll GitHub Events API.
2. **Queue:** event hợp lệ được publish vào Kafka.
3. **Streaming:** Spark Structured Streaming đọc từ Kafka.
4. **Storage:** dữ liệu được ghi vào ClickHouse để query nhanh và Parquet để archive/backfill.
5. **Serving:** FastAPI đọc ClickHouse và các repository liên quan để tạo dashboard/intelligence payload.
6. **Presentation:** React dashboard hiển thị trạng thái pipeline, repo trending, breakout, rotation, news impact, và radar.

## 3. Actor chính trong hệ thống

| Actor | Mô tả | Nhu cầu chính |
| --- | --- | --- |
| Dashboard User / Analyst | Người xem dashboard, làm phân tích sản phẩm/công nghệ | Hiểu repo/framework/ecosystem nào đang tăng attention |
| Product/Business Stakeholder | Người dùng insight để ra quyết định hoặc báo cáo | Có slide/brief dễ hiểu về xu hướng GitHub |
| Pipeline Operator / Developer | Người vận hành backend/pipeline | Kiểm tra health, chạy ingestion, xử lý lỗi pipeline |
| Frontend Client | Ứng dụng React gọi API backend | Lấy dữ liệu đã chuẩn hóa để render UI |
| External Source Operator | Người quản lý nguồn tin tức bên ngoài | Preview/sync RSS/news official sources |
| External Systems | GitHub Events API, Kafka, Spark, ClickHouse, Parquet, RSS sources | Cung cấp/hạ tầng xử lý/lưu trữ dữ liệu |

## 4. Nhóm use case tổng quan

Có thể chia use case của dự án thành 4 nhóm lớn:

1. **Pipeline Operations**
   - Kiểm tra health/status.
   - Ingest GitHub events.
   - Process event stream.
   - Sync/discover repository metadata.

2. **Dashboard Analytics**
   - Xem latest events.
   - Xem top repositories.
   - Xem trending repositories.
   - Xem topic/language/category rotation.
   - Xem repo time series và shock movers.

3. **Intelligence Product**
   - Breakout Detector.
   - Ecosystem Rotation.
   - News Impact.
   - Framework/Competitive Radar.

4. **External Data Control**
   - Preview external news sources.
   - Sync external news sources.
   - Kiểm tra readiness/latest/health của news source ingestion.

---

# 5. Use Case 1 — Kiểm tra sức khỏe hệ thống

## Mục tiêu

Cho frontend hoặc operator biết API, ClickHouse, dữ liệu Parquet và pipeline có đang hoạt động bình thường hay không.

## Actor

- Dashboard user.
- Pipeline operator.
- Frontend runtime banner.

## Endpoint/API liên quan

- `GET /health`
- `GET /pipeline/status`

## Luồng chính

```text
User/Frontend
  -> FastAPI /health hoặc /pipeline/status
  -> Backend kiểm tra API process, ClickHouse, Parquet/data freshness
  -> Trả về trạng thái ok/healthy/degraded và metadata vận hành
```

## Ý nghĩa nghiệp vụ

Use case này là điểm bắt đầu của dashboard. Nếu pipeline bị lỗi hoặc dữ liệu không mới, mọi insight phía sau đều có nguy cơ gây hiểu nhầm. Vì vậy dashboard cần hiển thị trạng thái runtime trước khi người dùng đọc analytics.

## Dữ liệu đầu vào

- Không cần input phức tạp.
- Có thể dựa vào config runtime, kết nối ClickHouse, thư mục Parquet và thời gian dữ liệu gần nhất.

## Dữ liệu đầu ra

- API status.
- ClickHouse status.
- Parquet/archive status.
- Pipeline freshness.
- Các cờ cảnh báo nếu degraded.

## Mức độ hiện tại

Đã có backend route và được frontend runtime status/banner sử dụng.

## File liên quan

- `src/presentation/api/routes.py`
- `docs/backend.md`
- `frontend/src/components/Overview.tsx`
- `frontend/src/hooks/useDashboardData.ts`

---

# 6. Use Case 2 — Ingest GitHub Events

## Mục tiêu

Thu thập GitHub events từ GitHub Events API, lọc event phù hợp, chuẩn hóa và đẩy vào Kafka để pipeline phía sau xử lý.

## Actor

- Pipeline operator/developer.
- GitHub Events API.
- Kafka producer.

## Application use case

- `PollGithubEventsUseCase`

## Luồng chính

```text
Operator chạy ingestion job
  -> PollGithubEventsUseCase gọi GitHub client
  -> Nhận raw GitHub events
  -> Lọc event theo rule cấu hình
  -> Map raw event sang DTO/domain entity
  -> Publish event hợp lệ vào Kafka topic
```

## Luồng ngoại lệ

- GitHub API lỗi hoặc rate limit: use case cần ghi log và xử lý lỗi thay vì làm sập toàn bộ hệ thống.
- Event không hợp lệ: bị filter/skip.
- Kafka publish lỗi: cần surface lỗi cho operator.

## Ý nghĩa nghiệp vụ

Đây là cửa vào của toàn bộ hệ thống. Nếu ingestion không ổn định, dashboard sẽ không có dữ liệu mới. Trong slide có thể trình bày đây là bước biến GitHub activity công khai thành event stream nội bộ.

## Dữ liệu đầu vào

- Raw GitHub Event từ GitHub Events API.
- Filter configuration.
- Kafka topic configuration.

## Dữ liệu đầu ra

- Kafka messages chứa event đã chuẩn hóa.
- Log vận hành.

## Mức độ hiện tại

Đã có use case và test cho happy path, filtering, error handling.

## File liên quan

- `src/application/use_cases/poll_github_events.py`
- `src/infrastructure/github/client.py`
- `src/infrastructure/kafka`
- `tests/application/test_poll_github_events.py`

---

# 7. Use Case 3 — Xử lý Event Stream

## Mục tiêu

Đọc event từ Kafka, xử lý bằng Spark Structured Streaming, ghi dữ liệu vào ClickHouse để phục vụ dashboard và Parquet để archive/backfill.

## Actor

- Pipeline operator.
- Spark streaming job.
- Kafka.
- ClickHouse.
- Parquet storage.

## Application use case

- `ProcessEventStreamUseCase`

## Luồng chính

```text
Operator chạy processing job
  -> ProcessEventStreamUseCase khởi động Spark job
  -> Spark đọc Kafka source
  -> Parse/normalize event payload
  -> Ghi serving data vào ClickHouse
  -> Ghi archive data vào Parquet
```

## Ý nghĩa nghiệp vụ

Use case này biến event stream thô thành dữ liệu có thể query. ClickHouse là nguồn online serving cho dashboard, còn Parquet là nguồn lưu trữ lâu dài/backfill.

## Dữ liệu đầu vào

- Kafka stream.
- Spark configuration.
- ClickHouse sink configuration.
- Parquet output path.

## Dữ liệu đầu ra

- Bảng ClickHouse có dữ liệu events/analytics.
- File Parquet archive.
- Streaming checkpoint/log.

## Mức độ hiện tại

Đã có application use case và infrastructure Spark streaming job.

## File liên quan

- `src/application/use_cases/process_event_stream.py`
- `src/infrastructure/spark/streaming_job.py`
- `src/infrastructure/storage`
- `docs/database.md`

---

# 8. Use Case 4 — Xem Latest GitHub Events

## Mục tiêu

Cho người dùng xem những GitHub events mới nhất đang được hệ thống ghi nhận.

## Actor

- Dashboard user.
- Frontend Overview.

## Endpoint/API liên quan

- `GET /events/latest`

## Luồng chính

```text
Frontend Overview
  -> GET /events/latest
  -> Backend đọc ClickHouse theo date range hiện tại
  -> Có thể filter theo event_type
  -> Trả về danh sách event mới nhất
  -> Frontend render activity feed/table
```

## Ý nghĩa nghiệp vụ

Use case này giúp chứng minh pipeline đang lấy dữ liệu thật và cho người dùng cảm giác về nhịp hoạt động hiện tại của GitHub.

## Dữ liệu đầu vào

- `limit` hoặc số lượng event cần lấy.
- `event_type` nếu muốn lọc.

## Dữ liệu đầu ra

- Event id.
- Event type.
- Actor.
- Repository.
- Timestamp.
- Metadata liên quan nếu có.

## Mức độ hiện tại

Đã có route backend và frontend dùng trong overview/dashboard data hook.

## File liên quan

- `src/presentation/api/routes.py`
- `frontend/src/components/Overview.tsx`
- `frontend/src/hooks/useDashboardData.ts`

---

# 9. Use Case 5 — Dashboard Overview / Top Repositories / Trending

## Mục tiêu

Cung cấp bức tranh tổng quan về repository nổi bật, repo đang trending, top movers và một số phân bố analytics chính.

## Actor

- Dashboard user.
- Analyst.
- Product stakeholder.

## Endpoint/API liên quan

- `GET /dashboard/top-repos`
- `GET /dashboard/trending`
- `GET /dashboard/topic-rotation`
- `GET /dashboard/repo-timeseries`

## Luồng chính

```text
Frontend dashboard
  -> Gọi các dashboard endpoints
  -> ClickHouseDashboardService chạy query analytics
  -> Backend trả response đã chuẩn hóa
  -> Frontend render card, chart, table, movement indicators
```

## Ý nghĩa nghiệp vụ

Đây là phần dễ đưa vào slide nhất để trả lời câu hỏi: “Hiện tại cộng đồng GitHub đang chú ý tới repository/topic nào?”.

## Dữ liệu đầu vào

- Khoảng thời gian.
- Limit.
- Category/topic/language nếu có.
- Repository name nếu xem time series.

## Dữ liệu đầu ra

- Danh sách top repo.
- Điểm attention/momentum.
- Star/fork/watch/event metrics tùy query.
- Trending score.
- Topic/category movement.
- Time series theo repo.

## Mức độ hiện tại

Các endpoint dashboard live đã có và được frontend gọi trực tiếp.

## File liên quan

- `src/presentation/api/dashboard_routes.py`
- `src/infrastructure/storage/clickhouse_dashboard_service.py`
- `frontend/src/components/Overview.tsx`
- `frontend/src/hooks/useDashboardData.ts`
- `frontend/src/hooks/useRepoTimeseries.ts`

---

# 10. Use Case 6 — Breakout Detector

## Mục tiêu

Phát hiện các repository có dấu hiệu “breakout”: tăng trưởng attention bất thường, có momentum tốt, hoặc có shock movement so với nền lịch sử.

## Actor

- Analyst.
- Dashboard user.
- Product/business stakeholder muốn tìm xu hướng sớm.

## Endpoint/API liên quan

- `GET /intelligence/breakout`

## Application use case

- `BuildBreakoutViewUseCase`

## Luồng chính

```text
Frontend BreakoutDetector
  -> GET /intelligence/breakout
  -> BuildBreakoutViewUseCase lấy top repos/shock movers từ dashboard reader
  -> Tính breakout score, durability, hype risk, confidence
  -> Trả danh sách repo breakout
  -> Frontend hiển thị ranking và lý do repo nổi bật
```

## Ý nghĩa nghiệp vụ

Use case này chuyển từ dashboard analytics sang “intelligence”. Thay vì chỉ xem số liệu, hệ thống cố gắng trả lời: “Repo nào đáng chú ý sớm trước khi nó trở nên quá phổ biến?”.

## Khái niệm quan trọng

| Khái niệm | Ý nghĩa |
| --- | --- |
| Breakout score | Điểm tổng hợp cho khả năng repo đang bứt phá |
| Durability | Mức độ bền của xu hướng, tránh chỉ spike ngắn hạn |
| Hype risk | Rủi ro repo chỉ đang hype nhất thời |
| Confidence | Độ tin cậy của kết luận dựa trên dữ liệu hiện có |

## Dữ liệu đầu vào

- Top repositories.
- Shock movers.
- Time series/momentum signals.
- Metadata repo/category nếu có.

## Dữ liệu đầu ra

- Danh sách breakout repo.
- Score và ranking.
- Lý do/driver.
- Confidence/hype risk.

## Mức độ hiện tại

Đã có backend intelligence endpoint, frontend component/hook và test application.

## File liên quan

- `src/application/use_cases/build_breakout_view.py`
- `src/presentation/api/intelligence_routes.py`
- `frontend/src/components/BreakoutDetector.tsx`
- `frontend/src/hooks/useBreakoutData.ts`
- `tests/application/test_build_breakout_view.py`

---

# 11. Use Case 7 — Ecosystem / Topic Rotation

## Mục tiêu

Phân tích sự dịch chuyển attention giữa các ecosystem, category hoặc topic. Ví dụ: AI tooling, web frameworks, databases, devtools, infrastructure… nhóm nào đang tăng hoặc giảm sức hút.

## Actor

- Analyst.
- Dashboard user.
- Người làm báo cáo xu hướng công nghệ.

## Endpoint/API liên quan

- `GET /intelligence/rotation`
- Một phần dữ liệu có thể liên quan tới `GET /dashboard/topic-rotation`

## Application use case

- `BuildRotationViewUseCase`

## Luồng chính

```text
Frontend EcosystemRotation
  -> GET /intelligence/rotation
  -> BuildRotationViewUseCase đọc topic/category rotation
  -> Backend map raw topics thành taxonomy product-facing
  -> Tính attention delta và drivers
  -> Frontend render category cards/charts
```

## Ý nghĩa nghiệp vụ

Use case này trả lời câu hỏi cấp cao hơn repo: “Dòng tiền chú ý của cộng đồng developer đang dịch chuyển sang ecosystem nào?”. Nó phù hợp để làm slide về market/technology trend.

## Dữ liệu đầu vào

- Topic/category analytics.
- Top repos theo category.
- Attention delta theo thời gian.
- Taxonomy mapping.

## Dữ liệu đầu ra

- Category/ecosystem name.
- Attention tăng/giảm.
- Driver repositories.
- Top topics.
- Confidence hoặc maturity nếu có.

## Mức độ hiện tại

Đã có backend intelligence route và frontend view live backend rotation intelligence với taxonomy-aware categories.

## File liên quan

- `src/application/use_cases/build_rotation_view.py`
- `src/presentation/api/intelligence_routes.py`
- `frontend/src/components/EcosystemRotation.tsx`
- `frontend/src/hooks/useRotationData.ts`
- `tests/application/test_build_rotation_view.py`

---

# 12. Use Case 8 — News Impact

## Mục tiêu

Liên hệ tin tức/sự kiện bên ngoài với biến động trên GitHub để đánh giá tác động của news lên repository, framework hoặc ecosystem.

Ví dụ câu hỏi mà use case này hướng tới:

- Một release/framework announcement có làm repo tăng stars/events không?
- Một tin tức AI/devtool có kéo attention sang category nào không?
- Tin nào có impact thật, tin nào chỉ là nhiễu?

## Actor

- Analyst.
- Dashboard user.
- External source operator.

## Endpoint/API liên quan

- `GET /intelligence/news-impact`
- `GET /intelligence/news-impact/{event_id}`
- `GET /intelligence/news-impact/readiness`
- `GET /intelligence/news-impact/sources/preview`
- `POST /intelligence/news-impact/sources/sync`
- `GET /intelligence/news-impact/sources/latest`
- `GET /intelligence/news-impact/sources/health`

## Application use cases

- `GetNewsImpactSnapshotUseCase`
- `GetNewsImpactReadinessUseCase`
- `PreviewExternalNewsSourcesUseCase`
- `SyncExternalNewsSourcesUseCase`
- `ListPersistedExternalNewsUseCase`

## Luồng chính — sync nguồn tin

```text
Operator
  -> Preview external news sources
  -> Backend fetch RSS/official-source items
  -> Operator/Job sync nguồn tin
  -> Persist external news items vào ClickHouse
  -> Đánh dấu duplicate hoặc low-confidence nếu có
```

## Luồng chính — xem news impact

```text
Frontend NewsImpact
  -> GET /intelligence/news-impact
  -> Backend lấy persisted news items
  -> Link news với repo/framework/category liên quan
  -> Đọc telemetry GitHub quanh thời điểm news
  -> Tính impact/causality/confidence
  -> Frontend render danh sách news impact và detail drill-down
```

## Ý nghĩa nghiệp vụ

Đây là use case quan trọng để biến dashboard từ “chỉ nhìn GitHub data” thành “giải thích vì sao dữ liệu biến động”. Nó kết nối external context với telemetry nội bộ.

## Khái niệm quan trọng

| Khái niệm | Ý nghĩa |
| --- | --- |
| External news item | Bài viết/thông báo/release từ nguồn bên ngoài |
| Entity linking | Liên kết news với repo/framework/category |
| Impact score | Mức độ tác động ước tính lên GitHub telemetry |
| Causality score | Độ hợp lý rằng news là nguyên nhân của biến động |
| Duplicate quarantine | Cờ loại trừ hoặc cảnh báo tin trùng |
| Low-confidence quarantine | Cờ cảnh báo item có độ tin cậy thấp |

## Dữ liệu đầu vào

- RSS/official source items.
- Persisted external news.
- Repo telemetry từ ClickHouse.
- Framework/category taxonomy.

## Dữ liệu đầu ra

- News impact snapshot.
- Detail theo event/news item.
- Linked repositories/frameworks/categories.
- Impact/causality/confidence.
- Source health/readiness/latest metadata.

## Mức độ hiện tại

Đã có backend computed intelligence từ persisted official-source items, duplicate/low-confidence flags ở ingestion, frontend NewsImpact và các operation endpoint cho source preview/sync/health.

## File liên quan

- `src/application/use_cases/get_news_impact_snapshot.py`
- `src/application/use_cases/get_news_impact_readiness.py`
- `src/application/use_cases/preview_external_news_sources.py`
- `src/application/use_cases/sync_external_news_sources.py`
- `src/application/use_cases/list_persisted_external_news.py`
- `src/infrastructure/external_sources`
- `src/infrastructure/storage/clickhouse_external_news_repository.py`
- `src/presentation/api/intelligence_routes.py`
- `frontend/src/components/NewsImpact.tsx`
- `frontend/src/hooks/useNewsImpactData.ts`
- `tests/application/test_get_news_impact_snapshot.py`

---

# 13. Use Case 9 — Framework / Competitive Radar

## Mục tiêu

So sánh framework hoặc technology category theo momentum, adoption, attention và risk dựa trên GitHub telemetry.

## Actor

- Analyst.
- Dashboard user.
- Người làm báo cáo cạnh tranh công nghệ.

## Endpoint/API liên quan

- `GET /intelligence/framework-radar`

## Application use case

- `GetFrameworkRadarSnapshotUseCase`

## Luồng chính

```text
Frontend CompetitiveRadar
  -> GET /intelligence/framework-radar
  -> GetFrameworkRadarSnapshotUseCase đọc top repos/trending analytics
  -> Gom repo theo framework/category
  -> Tính radar metrics: momentum, adoption, risk, maturity
  -> Frontend render competitive/radar view
```

## Ý nghĩa nghiệp vụ

Use case này phù hợp cho slide so sánh công nghệ. Thay vì chỉ nói “framework A nổi hơn framework B”, hệ thống có thể trình bày nhiều trục: adoption, momentum, hype risk, confidence.

## Dữ liệu đầu vào

- Top repositories.
- Trending repositories.
- Repo metadata/category.
- Topic/language signals.

## Dữ liệu đầu ra

- Framework/category radar snapshot.
- Metrics theo framework.
- Ranking/comparison.
- Risk/confidence nếu có.

## Mức độ hiện tại

Đã có backend tính framework metrics từ live repository analytics thay vì fixed snapshot, frontend CompetitiveRadar và tests.

## File liên quan

- `src/application/use_cases/get_framework_radar_snapshot.py`
- `src/presentation/api/intelligence_routes.py`
- `frontend/src/components/CompetitiveRadar.tsx`
- `frontend/src/hooks/useFrameworkRadarData.ts`
- `tests/application/test_get_framework_radar_snapshot.py`

---

# 14. Use Case 11 — Discover Repository Catalog

## Mục tiêu

Phát hiện repository catalog từ GitHub để có danh sách repo quan trọng phục vụ metadata enrichment và analytics.

## Actor

- Operator/developer.
- GitHub API.
- Metadata repository.

## Application use case

- `DiscoverRepoCatalogUseCase`

## Luồng chính

```text
Operator chạy discovery
  -> DiscoverRepoCatalogUseCase gọi GitHub search/client
  -> Lấy repository candidates theo stars/category/query
  -> Parse raw metadata
  -> Chuẩn hóa repo catalog
  -> Lưu hoặc chuyển tiếp cho metadata sync
```

## Ý nghĩa nghiệp vụ

Raw GitHub events cho biết hoạt động, nhưng để phân tích theo category/framework/topic cần metadata tốt. Repository catalog giúp hệ thống biết repo nào đáng theo dõi và enrich.

## Dữ liệu đầu vào

- GitHub search query.
- Star threshold/category criteria.
- Pagination/config.

## Dữ liệu đầu ra

- Danh sách repository candidates.
- Metadata cơ bản: name, owner, stars, language, topics, description.

## Mức độ hiện tại

Đã có application use case và tests.

## File liên quan

- `src/application/use_cases/discover_repo_catalog.py`
- `src/infrastructure/github/client.py`
- `tests/application/test_discover_repo_catalog.py`

---

# 16. Use Case 12 — Sync Repository Metadata

## Mục tiêu

Đồng bộ metadata repository để analytics/intelligence có thêm context như category, topic, language, stars, forks, description.

## Actor

- Operator/developer.
- GitHub API.
- ClickHouse/repository metadata store.

## Application use case

- `SyncRepoMetadataUseCase`

## Luồng chính

```text
Operator chạy metadata sync
  -> SyncRepoMetadataUseCase nhận danh sách repo hoặc criteria
  -> Gọi GitHub client lấy metadata mới nhất
  -> Chuẩn hóa/category hóa metadata
  -> Persist vào metadata repository
  -> Dashboard/intelligence dùng metadata để phân tích tốt hơn
```

## Ý nghĩa nghiệp vụ

Nếu thiếu metadata, hệ thống chỉ biết event đến từ repo nào nhưng khó hiểu repo thuộc nhóm công nghệ nào. Metadata sync giúp các use case như Ecosystem Rotation, Framework Radar và News Impact chính xác hơn.

## Dữ liệu đầu vào

- Repository list/catalog.
- GitHub metadata response.
- Category classifier/taxonomy.

## Dữ liệu đầu ra

- Metadata repository đã cập nhật.
- Category/language/topic fields phục vụ query.

## Mức độ hiện tại

Đã có use case và tests. Docs backend ghi nhận category logic trong ingestion còn đơn giản, nhưng intelligence route đã map raw topics sang taxonomy product-facing.

## File liên quan

- `src/application/use_cases/sync_repo_metadata.py`
- `src/domain/services/category_classifier.py`
- `src/infrastructure/storage/clickhouse_repo_metadata_repository.py`
- `tests/application/test_sync_repo_metadata.py`

---

# 17. Use Case 13 — External News Source Preview/Sync/Health

## Mục tiêu

Quản lý vòng đời nguồn tin bên ngoài cho News Impact: kiểm tra nguồn, xem trước item, sync item vào storage và theo dõi health/latest.

## Actor

- External source operator.
- Analyst.
- Backend job.

## Endpoint/API liên quan

- `GET /intelligence/news-impact/sources/preview`
- `POST /intelligence/news-impact/sources/sync`
- `GET /intelligence/news-impact/sources/latest`
- `GET /intelligence/news-impact/sources/health`
- `GET /intelligence/news-impact/readiness`

## Application use cases

- `PreviewExternalNewsSourcesUseCase`
- `SyncExternalNewsSourcesUseCase`
- `GetNewsImpactReadinessUseCase`
- `ListPersistedExternalNewsUseCase`

## Luồng chính

```text
Operator kiểm tra nguồn
  -> Preview sources
  -> Backend fetch RSS/external source nhưng chưa persist
  -> Operator xem item có hợp lệ không

Operator sync
  -> POST sync
  -> Backend fetch và persist item
  -> Backend đánh dấu duplicate/low-confidence nếu cần

Dashboard kiểm tra readiness
  -> GET readiness/latest/health
  -> Biết dữ liệu news đã sẵn sàng cho NewsImpact chưa
```

## Ý nghĩa nghiệp vụ

Use case này là phần “data governance” của News Impact. Nó đảm bảo insight không dựa trên nguồn tin mơ hồ hoặc dữ liệu chưa sync.

## Dữ liệu đầu vào

- RSS/external source config.
- News item payload.
- Existing persisted items để detect duplicate.

## Dữ liệu đầu ra

- Preview item list.
- Persisted external news.
- Health/readiness/latest metadata.
- Duplicate/low-confidence flags.

## Mức độ hiện tại

Đã có endpoint và use case cho preview, sync, latest, health, readiness.

## File liên quan

- `src/application/use_cases/preview_external_news_sources.py`
- `src/application/use_cases/sync_external_news_sources.py`
- `src/application/use_cases/get_news_impact_readiness.py`
- `src/application/use_cases/list_persisted_external_news.py`
- `src/infrastructure/external_sources`
- `src/presentation/api/intelligence_routes.py`

---

# 18. Frontend user journeys

## 18.1 Journey: Người dùng mở dashboard để xem tình hình hệ thống

```text
Mở frontend
  -> App load runtime config VITE_API_BASE_URL
  -> Overview gọi pipeline status/latest events/top repos/trending
  -> User thấy hệ thống có dữ liệu mới không
  -> User xem repo/top movers hiện tại
```

Component/hook chính:

- `frontend/src/App.tsx`
- `frontend/src/components/Overview.tsx`
- `frontend/src/hooks/useDashboardData.ts`
- `frontend/src/lib/api.ts`

## 18.2 Journey: Analyst tìm repo có khả năng breakout

```text
Mở tab Breakout Detector
  -> Frontend gọi /intelligence/breakout
  -> Backend tính breakout ranking
  -> User xem repo nào tăng attention bất thường
  -> User dùng repo đó làm case study trong slide
```

Component/hook chính:

- `frontend/src/components/BreakoutDetector.tsx`
- `frontend/src/hooks/useBreakoutData.ts`

## 18.3 Journey: Analyst xem ecosystem nào đang dịch chuyển

```text
Mở tab Ecosystem Rotation
  -> Frontend gọi /intelligence/rotation
  -> Backend trả category rotation và drivers
  -> User xem nhóm công nghệ nào đang tăng/giảm
  -> User đưa vào slide trend/ecosystem
```

Component/hook chính:

- `frontend/src/components/EcosystemRotation.tsx`
- `frontend/src/hooks/useRotationData.ts`

## 18.4 Journey: Analyst giải thích biến động bằng tin tức bên ngoài

```text
Operator sync news sources
  -> News items được persist
  -> User mở News Impact
  -> Frontend gọi /intelligence/news-impact
  -> Backend link news với repo/framework/category
  -> User xem tin nào có impact lên GitHub telemetry
```

Component/hook chính:

- `frontend/src/components/NewsImpact.tsx`
- `frontend/src/hooks/useNewsImpactData.ts`

## 18.5 Journey: Stakeholder so sánh framework

```text
Mở Competitive Radar
  -> Frontend gọi /intelligence/framework-radar
  -> Backend tính radar metrics từ live repo analytics
  -> User so sánh framework theo momentum/adoption/risk
```

Component/hook chính:

- `frontend/src/components/CompetitiveRadar.tsx`
- `frontend/src/hooks/useFrameworkRadarData.ts`

---

# 19. Mapping use case sang API và frontend

| Use case | API/backend | Frontend |
| --- | --- | --- |
| Health/status | `/health`, `/pipeline/status` | Overview/runtime banner |
| Latest events | `/events/latest` | Overview |
| Top repos | `/dashboard/top-repos` | Overview/Breakout-related views |
| Trending | `/dashboard/trending` | Overview |
| Topic rotation | `/dashboard/topic-rotation`, `/intelligence/rotation` | EcosystemRotation |
| Repo time series | `/dashboard/repo-timeseries` | BreakoutDetector/time series hooks |
| Breakout Detector | `/intelligence/breakout` | BreakoutDetector |
| News Impact | `/intelligence/news-impact`, detail/readiness/source endpoints | NewsImpact |
| Framework Radar | `/intelligence/framework-radar` | CompetitiveRadar |
| External source control | preview/sync/latest/health endpoints | NewsImpact operations/data readiness |

---

# 20. Maturity hiện tại của các use case

| Use case | Mức độ hiện tại | Ghi chú |
| --- | --- | --- |
| Health/status | Live | Dùng để kiểm tra API/pipeline/storage |
| Ingest GitHub events | Implemented | Có use case và tests |
| Process event stream | Implemented | Kafka -> Spark -> ClickHouse/Parquet |
| Latest events | Live | Frontend gọi backend trực tiếp |
| Dashboard top/trending/time series | Live | Dựa trên ClickHouseDashboardService |
| Breakout Detector | Live intelligence | Có endpoint, frontend, tests |
| Ecosystem Rotation | Live intelligence | Có taxonomy-aware categories |
| News Impact | Computed intelligence | Có source operations, persisted official-source items |
| Framework Radar | Computed intelligence | Dựa trên live repo analytics, không còn fixed snapshot đơn thuần |
| Repo catalog discovery | Backend/operator use case | Hỗ trợ metadata enrichment |
| Repo metadata sync | Backend/operator use case | Hỗ trợ category/framework/topic analytics |

---

# 21. Cách kể câu chuyện này trên slide

## Slide 1 — Vấn đề

- GitHub có rất nhiều tín hiệu về xu hướng công nghệ nhưng dữ liệu rời rạc.
- Người dùng khó biết repo/framework/ecosystem nào thật sự đang tăng trưởng.
- Cần một hệ thống thu thập, xử lý và biến telemetry thành insight.

## Slide 2 — Giải pháp

- GitHub Analyzer ingest GitHub Events.
- Xử lý stream bằng Kafka + Spark.
- Lưu ClickHouse để query analytics nhanh.
- Frontend dashboard hiển thị insight theo nhiều use case.

## Slide 3 — Kiến trúc dữ liệu

Dùng sơ đồ:

```text
GitHub Events API -> Kafka -> Spark -> ClickHouse/Parquet -> FastAPI -> React Dashboard
```

Nhấn mạnh:

- ClickHouse: serving analytics.
- Parquet: archive/backfill.
- FastAPI: contract ổn định cho frontend.

## Slide 4 — Nhóm use case vận hành

- Health/status.
- Poll GitHub events.
- Process event stream.
- Sync repo metadata.

Thông điệp: hệ thống có pipeline thật, không chỉ UI mock.

## Slide 5 — Nhóm use case dashboard analytics

- Latest events.
- Top repositories.
- Trending repositories.
- Topic rotation.
- Repo time series.

Thông điệp: biến dữ liệu thô thành số liệu quan sát được.

## Slide 6 — Nhóm use case intelligence

- Breakout Detector.
- Ecosystem Rotation.
- News Impact.
- Framework Radar.

Thông điệp: không chỉ hiển thị số liệu, mà còn diễn giải xu hướng.

## Slide 7 — Deep dive Breakout Detector

- Input: top repos, shock movers, time series.
- Processing: tính breakout score, durability, hype risk, confidence.
- Output: repo đáng chú ý sớm.

## Slide 8 — Deep dive News Impact

- Input: external news + GitHub telemetry.
- Processing: entity linking, impact/causality scoring.
- Output: giải thích biến động GitHub bằng context bên ngoài.

## Slide 9 — Deep dive Framework Radar

- Input: repo analytics + metadata/category.
- Processing: gom nhóm theo framework/category, tính momentum/adoption/risk.
- Output: radar so sánh công nghệ.

## Slide 10 — Hiện trạng và hướng phát triển

Hiện trạng:

- Core pipeline và nhiều endpoint live đã có.
- Intelligence routes đã bắt đầu computed từ backend.

Hướng phát triển:

- Entity linking sâu hơn cho News Impact.
- Causality scoring tốt hơn.
- Framework/category marts thay heuristic matching.
- Guardrails và confidence scoring rõ hơn.

---

# 22. Kết luận

Dự án hiện không chỉ có một dashboard đơn giản mà là một hệ thống nhiều tầng:

1. **Data pipeline:** lấy GitHub events và xử lý dữ liệu lớn.
2. **Analytics backend:** query ClickHouse để tạo dashboard metrics.
3. **Intelligence layer:** diễn giải breakout, ecosystem rotation, news impact, radar và brief.
4. **Frontend presentation:** biến dữ liệu thành trải nghiệm trực quan để báo cáo.

Nếu làm slide, nên nhấn mạnh rằng giá trị cốt lõi của dự án nằm ở việc chuyển đổi:

```text
Raw GitHub activity -> Structured telemetry -> Analytics metrics -> Product intelligence -> Reportable insight
```
