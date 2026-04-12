# Observation and Tracing Presentation Plan

## 1. Overview

Tài liệu này là kịch bản nội dung cho phần thuyết trình đề tài `Observability and Tracing`
trong môn `Phát Triển Phần Mềm Hướng Dịch Vụ`.

Phiên bản này chọn một hướng mạnh hơn hẳn để tránh lặp lại hai nhóm trước:

> `Healthy does not mean correct.`

Tức là:

- hệ thống có thể vẫn trả `200 OK`
- dashboard hạ tầng vẫn còn xanh
- nhưng business flow đã sai hoặc đã ngừng tạo giá trị

Mục tiêu không phải lặp lại toàn bộ lý thuyết mà hai nhóm trước đã trình bày, mà là:

- tóm lược đủ chắc phần nền tảng để bài nói vẫn đầy đặn và không hời hợt
- tái đóng khung vấn đề theo hướng điều tra sự cố thực chiến
- làm rõ giá trị của observability trong hệ thống dịch vụ nhiều thành phần
- chuẩn bị đà cho một màn demo có chủ đích, không phải demo công cụ đơn thuần
- biến bài nói thành một câu chuyện điều tra thay vì một bài tổng hợp lý thuyết

Thời lượng được chia như sau:

- `14 phút` thuyết trình
- `11 phút` demo

Đề xuất tổng số slide:

- `15 slide` cho phần trình bày
- không nhồi chữ, ưu tiên 1 ý chính mỗi slide

Thông điệp xuyên suốt của cả bài:

> Observability không chỉ trả lời hệ thống có đang sống hay không, mà trả lời vì sao hệ
> thống đang hành xử như vậy.

Thông điệp mạnh hơn để tạo hiệu ứng `wow`:

> Trong microservices, thứ người dùng nhìn thấy thường chỉ là triệu chứng. Observability
> tồn tại để lần ra nguyên nhân gốc đang nằm ở một nơi khác.

Lưu ý thuật ngữ:

- Khi nói nên dùng từ `Observability`, không nên giải thích theo nghĩa `Observation`.
- Có thể mở lời rằng đề tài nhà trường ghi `Observation and Tracing`, nhưng trong kỹ thuật
  phần mềm và vận hành hệ thống, thuật ngữ chuẩn là `Observability and Tracing`.

## 2. Presentation Strategy

### 2.1 Bối cảnh cạnh tranh

Hai nhóm trước nhiều khả năng đã nói tương đối đủ các ý sau:

- định nghĩa observability
- ba trụ cột logs, metrics, traces
- khái niệm trace, span, trace ID
- giới thiệu OpenTelemetry, Tempo, Prometheus, Grafana
- demo xem trace trên UI

Nếu nhóm này đi lại đúng tuyến đó, rủi ro cao là bị ngắt nhịp kiểu `skip đi`.

### 2.2 Hướng tiếp cận đề xuất

Nhóm này nên chuyển tâm điểm từ `định nghĩa công cụ` sang `giải quyết sự cố trong hệ thống`.

Khung tư duy chính:

- monitoring cho biết `có vấn đề`
- observability giúp điều tra `vì sao có vấn đề`
- tracing cho biết `vấn đề nằm ở đâu trong chuỗi request`
- trong hệ thống dịch vụ, `healthy` chưa chắc đã `hoạt động đúng`

### 2.3 Wow Direction

Hướng nên chốt cho cả bài:

`The Green Dashboard Lied: Root Cause Analysis in Microservices`

Phiên bản tiếng Việt:

`Dashboard vẫn xanh, nhưng hệ thống đã sai: dùng observability để truy nguyên sự cố trong microservices`

Vì sao đây là hướng mạnh nhất:

- mở bài bằng một nghịch lý kỹ thuật thay vì định nghĩa
- khớp trực tiếp với học liệu của thầy:
  - health check API
  - application metrics
  - distributed tracing
- khớp với repo demo hiện có:
  - health endpoint
  - Prometheus metrics
  - Grafana dashboard
- tracing qua OpenTelemetry
- `X-Trace-Id` để correlation
- `X-Trace-Explore-Url` để mở trace drilldown nhanh trên Grafana
- dễ làm slide đẹp vì trọng tâm là sơ đồ luồng, kiến trúc và timeline sự cố

Nếu chỉ còn một câu để chốt hướng, hãy dùng câu này:

> Bài của nhóm em không trả lời Prometheus, Tempo, Grafana là gì, mà trả lời khi hệ thống
> trông vẫn ổn thì làm sao biết nó đang hỏng ở đâu.

### 2.4 Câu mở đầu đề xuất

> Như hai nhóm trước đã trình bày khá đầy đủ về khái niệm, thành phần và một số công cụ
> phổ biến, nhóm em xin phép tóm lược ngắn phần nền tảng để thống nhất cách hiểu. Sau đó,
> nhóm em tập trung vào một câu hỏi quan trọng hơn: nếu hệ thống vẫn còn sống, nhưng kết quả
> trả ra đã sai hoặc đã chậm bất thường, thì observability và tracing giúp chúng ta truy nguyên
> sự cố như thế nào?

Mục đích của câu mở đầu này:

- thể hiện tôn trọng nhóm trước
- xin quyền rút gọn phần lặp lại
- hợp thức hóa việc đi sâu vào insight và demo

## 3. Current Demo Asset In This Repository

Nhóm đang có lợi thế lớn vì demo không phải mô hình toy project mà là một hệ thống nhiều tầng:

- GitHub Events API
- Kafka
- Spark Structured Streaming
- ClickHouse
- FastAPI
- Next.js dashboard
- Prometheus
- Grafana
- Tempo
- OpenTelemetry

Điểm mạnh có thể tận dụng:

- có cả `metrics` và `tracing`
- có dashboard observability riêng
- API trả về `X-Trace-Id`
- có thể chứng minh tương quan giữa symptom và root cause
- có thể mô phỏng sự cố `API vẫn sống nhưng data flow bị hỏng`

Thông điệp cần rút ra từ hệ thống này:

> Trong môi trường dịch vụ phân tán, lỗi thường không xuất hiện ngay tại nơi người dùng nhìn
> thấy, mà nằm ở một thành phần trung gian như queue, processor, storage, hoặc external service.

## 4. Slide Map

### Slide 1. Title and Positioning

**Tiêu đề gợi ý**

`Healthy Does Not Mean Correct`

**Phụ đề**

`Root Cause Analysis in Service-Oriented Systems with Prometheus, Grafana and Tracing`

**Mục tiêu slide**

- giới thiệu đề tài
- định vị góc nhìn của nhóm

**Nội dung chính**

- tên đề tài
- tên 3 thành viên
- 1 câu phụ đề:
  `Từ dashboard còn xanh đến nguyên nhân gốc của sự cố`

**Người nói**

- Người 1

**Lời thoại gợi ý**

> Đề tài của nhóm em là Observability and Tracing trong hệ thống hướng dịch vụ. Nhưng thay vì
> bắt đầu từ định nghĩa, nhóm em bắt đầu từ một nghịch lý quen thuộc trong vận hành: dashboard
> vẫn xanh, API vẫn sống, nhưng hệ thống đã không còn hoạt động đúng.

---

### Slide 2. Why This Topic Still Matters

**Mục tiêu slide**

- trả lời câu hỏi `vì sao đã có 2 nhóm trước mà nhóm này vẫn đáng nghe`

**Nội dung chính**

- hai nhóm trước đã trình bày nền tảng khá đầy đủ
- nhóm này tập trung vào:
  - trực quan hóa lại ngắn gọn
  - đưa thêm góc nhìn vận hành
  - gắn với một hệ thống lớn hơn và demo sự cố

**Người nói**

- Người 1

**Lời thoại gợi ý**

> Như hai nhóm trước đã trình bày khá đầy đủ về lý thuyết và công cụ, nhóm em xin phép nhắc
> lại ngắn gọn phần nền tảng, sau đó đi vào phần mà theo nhóm là quan trọng nhất: giá trị của
> observability khi phải xử lý sự cố trong hệ thống nhiều service.

---

### Slide 3. Agenda

**Mục tiêu slide**

- cho thầy thấy bài nói có cấu trúc rõ ràng

**Nội dung chính**

1. Khái niệm cốt lõi
2. Insight thực chiến trong hệ dịch vụ
3. Kiến trúc demo của nhóm
4. Cách observability và tracing hỗ trợ điều tra sự cố
5. Demo live

**Người nói**

- Người 1

---

### Slide 4. Core Concepts Refresher

**Mục tiêu slide**

- nhắc lại đủ chắc nhưng không sa đà

**Nội dung chính**

- `Observability`: khả năng suy ra trạng thái bên trong hệ thống từ dữ liệu đầu ra
- `Tracing`: theo dõi đường đi của một request qua nhiều thành phần
- `Logs`: mô tả chi tiết từng sự kiện
- `Metrics`: đo lường tổng hợp theo thời gian
- `Traces`: thể hiện quan hệ nhân quả xuyên service

**Người nói**

- Người 1

**Lời thoại gợi ý**

> Nếu logs giúp ta đọc từng sự kiện, metrics giúp ta thấy xu hướng, thì traces cho ta thấy một
> request đã đi qua đâu và mất thời gian ở đâu. Ba thành phần này không thay thế nhau mà bổ sung
> cho nhau.

---

### Slide 5. Trace, Span, Trace ID

**Mục tiêu slide**

- giữ lại phần lý thuyết bắt buộc

**Nội dung chính**

- `Trace`: toàn bộ hành trình của một request
- `Span`: một bước công việc trong trace
- `Trace ID`: định danh toàn trace
- `Span ID`: định danh một span cụ thể
- `Parent-child relationship`: cho biết thứ tự và quan hệ gọi nhau

**Người nói**

- Người 1

**Trực quan nên có**

- sơ đồ 1 request đi qua API -> service -> DB

---

### Slide 6. Monitoring vs Observability

**Mục tiêu slide**

- bắt đầu chuyển sang phần có chiều sâu hơn

**Nội dung chính**

| Monitoring | Observability |
|---|---|
| Theo dõi chỉ số đã biết | Điều tra hành vi chưa biết trước |
| Trả lời `có vấn đề không` | Trả lời `vì sao có vấn đề` |
| Cảnh báo | Giải thích |

**Người nói**

- Người 2

**Lời thoại gợi ý**

> Monitoring rất quan trọng, nhưng nếu chỉ có monitoring thì ta mới biết hệ thống bất thường.
> Observability tiến thêm một bước: nó giúp kỹ sư lần ra nguyên nhân của sự bất thường đó.

---

### Slide 7. Healthy Does Not Mean Correct

**Mục tiêu slide**

- tạo điểm nhấn tư duy

**Nội dung chính**

- API `/health` trả về `200`
- dashboard vẫn mở được
- nhưng luồng dữ liệu có thể đã dừng
- business value không còn được tạo ra

**Người nói**

- Người 2

**Thông điệp chính**

> Một service còn sống không đồng nghĩa toàn bộ hệ thống còn hoạt động đúng.

**Đây là slide rất quan trọng** vì nó mở đường trực tiếp cho demo.

---

### Slide 8. Why Tracing Matters In Microservices

**Mục tiêu slide**

- nối từ observability chung sang tracing cụ thể

**Nội dung chính**

- request đi qua nhiều service
- lỗi có thể phát sinh ở service khác với nơi symptom xuất hiện
- tracing giúp:
  - theo dõi request xuyên service
  - so sánh thời gian từng bước
  - tìm bottleneck hoặc external dependency chậm

**Người nói**

- Người 2

---

### Slide 9. Incident Investigation Workflow

**Mục tiêu slide**

- cho thấy tracing không đứng riêng lẻ

**Nội dung chính**

1. Metrics phát hiện tín hiệu bất thường
2. Trace khoanh vùng request có vấn đề
3. Log xác nhận chi tiết lỗi
4. Kỹ sư sửa đúng chỗ thay vì đoán

**Người nói**

- Người 2

**Lời thoại gợi ý**

> Trong thực tế, kỹ sư hiếm khi nhìn trace trước. Thường chúng ta thấy metric bất thường trước,
> sau đó dùng trace để lần theo đường đi, rồi dùng log để xác nhận chính xác chuyện gì đã xảy ra.

---

### Slide 10. Demo System Architecture

**Mục tiêu slide**

- đưa bài về hệ thống của nhóm

**Nội dung chính**

- GitHub Events API
- Poller
- Kafka
- Processor
- ClickHouse + Parquet
- FastAPI + Frontend
- Prometheus + Grafana + Tempo

**Người nói**

- Người 2

**Trực quan nên có**

- sơ đồ kiến trúc đơn giản, màu khác cho:
  - business flow
  - observability flow

**Câu nhấn**

> Đây là lý do observability thực sự cần thiết: vì hệ thống không còn là một process duy nhất.

---

### Slide 11. What We Observe In This System

**Mục tiêu slide**

- gắn khái niệm với dữ liệu cụ thể nhóm có thể show

**Nội dung chính**

- `Metrics`:
  - API latency
  - request rate
  - data freshness
  - pipeline throughput
  - processor health
- `Tracing`:
  - trace theo request API
  - trace outbound call
  - `X-Trace-Id`
- `Operational signals`:
  - health check
  - data lag
  - Kafka lag

**Người nói**

- Người 3

---

### Slide 12. Demo Scenario

**Mục tiêu slide**

- công bố trước tình huống demo để người xem hiểu sẽ quan sát cái gì

**Tiêu đề gợi ý**

`Scenario: API Is Up, But The Data Pipeline Is Stale`

**Nội dung chính**

- giả lập processor ngừng xử lý
- người dùng vẫn thấy API còn sống
- nhưng dữ liệu mới không còn chảy vào hệ thống
- observability sẽ chỉ ra điều đó như thế nào

**Người nói**

- Người 3

**Lời thoại gợi ý**

> Đây là loại lỗi rất dễ đánh lừa người vận hành. Nếu chỉ nhìn health endpoint, ta tưởng hệ
> thống ổn. Nhưng nếu nhìn data freshness và throughput, ta biết giá trị thật mà hệ thống tạo ra
> đã bị dừng.

---

### Slide 13. What We Expect To See In Demo

**Mục tiêu slide**

- biến demo từ ngẫu hứng thành kiểm chứng có mục tiêu

**Nội dung chính**

- trước lỗi:
  - API healthy
  - throughput ổn định
  - freshness thấp
- khi lỗi xảy ra:
  - API vẫn healthy
  - throughput giảm hoặc dừng
  - freshness tăng
  - tracing hỗ trợ correlation với request
- sau khi khôi phục:
  - metric hồi phục

**Người nói**

- Người 3

---

### Slide 14. Key Takeaways

**Mục tiêu slide**

- chốt giá trị kỹ thuật

**Nội dung chính**

- observability không chỉ để giám sát
- tracing không chỉ để vẽ sơ đồ request
- trong hệ dịch vụ, điều quan trọng là:
  - phát hiện đúng
  - truy nguyên nhanh
  - giảm MTTR
  - tránh sửa sai chỗ

**Người nói**

- Người 3

---

### Slide 15. Transition To Live Demo

**Mục tiêu slide**

- nối mượt sang phần 11 phút demo

**Nội dung chính**

- 3 vai trong demo:
  - user view
  - fault injector
  - observability war room
- mục tiêu demo:
  - phát hiện vấn đề
  - truy nguyên
  - khôi phục

**Người nói**

- Người 3

**Lời thoại gợi ý**

> Sau đây nhóm em sẽ minh họa đúng kịch bản vừa trình bày: một thành phần xử lý bị dừng, hệ thống
> bề ngoài vẫn còn sống, nhưng observability sẽ cho thấy chính xác điều gì đang xảy ra.

## 5. Suggested Timing For 14-Minute Presentation

| Slide | Time | Speaker |
|---|---:|---|
| 1 | 0:40 | Người 1 |
| 2 | 0:50 | Người 1 |
| 3 | 0:30 | Người 1 |
| 4 | 1:10 | Người 1 |
| 5 | 1:10 | Người 1 |
| 6 | 1:10 | Người 2 |
| 7 | 1:00 | Người 2 |
| 8 | 1:00 | Người 2 |
| 9 | 1:10 | Người 2 |
| 10 | 1:10 | Người 2 |
| 11 | 1:10 | Người 3 |
| 12 | 1:10 | Người 3 |
| 13 | 1:00 | Người 3 |
| 14 | 0:50 | Người 3 |
| 15 | 0:30 | Người 3 |

Tổng thời gian xấp xỉ `14 phút`.

## 6. Role Split For 3 Presenters

### Người 1

Phụ trách:

- mở bài
- tóm lược khái niệm nền tảng
- thống nhất ngôn ngữ chuyên môn

Yêu cầu:

- nói chắc, rõ, tốc độ vừa phải
- không sa đà vào lịch sử công cụ
- kết thúc bằng câu bàn giao sang người 2

### Người 2

Phụ trách:

- phần insight thực chiến
- giải thích sự khác nhau giữa monitoring và observability
- giải thích vì sao microservices cần tracing
- trình bày kiến trúc hệ thống demo

Yêu cầu:

- đây là phần thể hiện chiều sâu học thuật nhất
- nên dùng ví dụ cụ thể, tránh nói chung chung

### Người 3

Phụ trách:

- kết nối observability với hệ thống của nhóm
- nêu kịch bản sự cố
- chốt expected outcome của demo
- chuyển sang live demo và kết luận

Yêu cầu:

- nói dứt khoát, câu ngắn
- phải làm người nghe muốn xem demo ngay

## 7. Demo Bridge

Phần thuyết trình phải chuẩn bị đà cho demo, nên cần nối rất mượt.

Mục tiêu của 11 phút demo:

1. chứng minh symptom và root cause không ở cùng một nơi
2. chứng minh chỉ nhìn health check là chưa đủ
3. chứng minh metrics và tracing phải đi cùng nhau

Flow demo đề xuất:

1. Mở dashboard hoặc `/pipeline/status`
2. Cho thấy hệ thống đang bình thường
3. Dừng processor
4. Chờ metric thay đổi
5. Cho thấy API vẫn sống nhưng freshness tăng và throughput giảm
6. Nếu có request trace, mở trực tiếp `X-Trace-Explore-Url`, hoặc dùng `X-Trace-Id` để tra trong Grafana Explore với Tempo
7. Khôi phục processor
8. Cho thấy metric hồi lại

## 8. Design Notes For The Slides

Để bài nhìn khác hai nhóm trước, slide nên theo nguyên tắc:

- ít bullet hơn, nhiều sơ đồ và flow hơn
- mỗi slide chỉ có 1 câu headline mạnh
- dùng màu nhất quán:
  - xanh cho normal
  - đỏ hoặc cam cho incident
  - tím hoặc xám cho observability signals
- có ít nhất 3 slide dạng trực quan:
  - trace flow
  - system architecture
  - incident workflow

Không nên:

- nhồi định nghĩa dài
- chụp quá nhiều ảnh tool UI ở phần trình bày
- đọc từng dòng bullet

## 8.1 Wow-First Visual Direction

Nguyên tắc thiết kế để slide ra đúng chất seminar này:

- slide phải trông như `technical investigation board`, không phải brochure công cụ
- ưu tiên sơ đồ khối, flow chart, incident timeline, trace waterfall, before-after comparison
- mỗi slide chỉ nên có:
  - `1 headline`
  - `1 hình minh họa chính`
  - `2-4 nhãn ngắn` nếu thật sự cần
- tỷ lệ nên hướng tới:
  - `70% hình minh họa kiến trúc / flow`
  - `20% nhãn ngắn`
  - `10% text giải thích`
- tuyệt đối `không dùng icon`
- không dùng layout marketing, không card nhỏ li ti, không ảnh stock

Nên có ít nhất các loại hình sau:

- sơ đồ kiến trúc hệ thống có hai lớp:
  - business flow
  - observability flow
- sơ đồ incident workflow:
  - symptom
  - metric anomaly
  - trace drilldown
  - root cause
- sơ đồ so sánh:
  - `healthy`
  - `correct`
- sơ đồ trace:
  - request path
  - span hierarchy
  - slow span highlighted

## 8.2 Gamma AI Master Prompt

Prompt cũ đúng ở mức ý tưởng tổng quát nhưng chưa đủ chặt để Gamma bám đúng narrative.
Vấn đề chính của prompt cũ là:

- chưa khóa cứng đúng `15 slide`
- chưa buộc Gamma đi đúng thứ tự của `Slide Map`
- chưa chỉ rõ visual chủ đạo của từng slide
- chưa cấm đủ mạnh các kiểu slide dễ làm deck bị lệch:
  - deck định nghĩa lý thuyết
  - deck giới thiệu công cụ
  - deck marketing nhiều card và icon

Prompt dưới đây được viết lại theo kiểu `deck specification`.
Mục tiêu là để Gamma tạo slide đúng với phân tích ở các mục trên, không suy diễn tự do.

```text
Tạo một bộ slide seminar kỹ thuật bằng TIẾNG VIỆT, gồm đúng 15 slide, cho môn Phát Triển Phần Mềm Hướng Dịch Vụ.

Chủ đề chính:
"Healthy Does Not Mean Correct"

Phụ đề:
"Từ dashboard còn xanh đến nguyên nhân gốc của sự cố trong microservices bằng Prometheus, Tempo và Grafana"

Đây là yêu cầu bắt buộc:
- Không tạo một deck giới thiệu observability chung chung.
- Không tạo một deck kiểu "Observability là gì?" từ đầu đến cuối.
- Không biến deck thành tài liệu lý thuyết nhiều chữ.
- Deck này phải là một câu chuyện điều tra sự cố trong hệ thống dịch vụ.

Bối cảnh lớp học:
- Hai nhóm trước đã trình bày khá nhiều về:
  observability,
  three pillars,
  trace/span/trace ID,
  OpenTelemetry,
  demo tracing cơ bản.
- Vì vậy deck này chỉ được phép nhắc lại phần nền tảng ở mức rất ngắn để thống nhất cách hiểu, rồi phải chuyển nhanh sang góc nhìn thực chiến.

Luận điểm trung tâm bắt buộc phải thể hiện rõ:
- hệ thống có thể vẫn sống
- API vẫn có thể trả 200 OK
- dashboard hạ tầng vẫn có thể còn xanh
- nhưng business flow đã sai, chậm, stale, hoặc ngừng tạo giá trị
- observability có giá trị vì nó giúp kỹ sư truy nguyên root cause nhanh hơn thay vì đoán

Ngữ cảnh demo thật của nhóm:
- Hệ thống demo là một pipeline nhiều tầng:
  GitHub Events API -> Poller -> Kafka -> Spark Structured Streaming -> ClickHouse + Parquet -> FastAPI -> Next.js Dashboard
- Stack observability của bài:
  Prometheus = metrics
  Tempo = tracing backend
  Grafana = mặt phẳng quan sát hợp nhất
- Có X-Trace-Id và X-Trace-Explore-Url để correlation và trace drilldown.
- Demo trọng tâm:
  API vẫn sống nhưng pipeline stale hoặc latency tăng,
  từ đó đi từ metric bất thường sang trace để khoanh vùng nguyên nhân.

Phong cách nội dung:
- kỹ thuật
- chắc
- gọn
- học thuật vừa đủ
- không marketing
- không màu mè
- không kể lịch sử công cụ
- không viết như giáo trình

Phong cách thiết kế:
- visual-first
- không icon
- không emoji
- không ảnh stock
- không template startup/product marketing
- không nhiều card nhỏ
- không nhồi bullet
- không làm slide giống textbook
- ưu tiên:
  architecture diagram
  service flow
  observability flow
  incident timeline
  trace waterfall
  before-after comparison
  layered diagnostic model

Quy tắc hình ảnh:
- mỗi slide chỉ có 1 visual chính
- visual phải chiếm khoảng 65-75% slide
- text chỉ là headline + vài nhãn ngắn
- tối đa 3 bullet rất ngắn nếu thực sự cần
- dùng màu có chủ đích:
  xanh/teal = normal flow
  cam/đỏ = incident hoặc anomaly
  xám = infrastructure / background

Quy tắc logic:
- mỗi slide phải có một headline ngắn, mạnh, dễ nói
- mỗi slide chỉ có một ý chính
- 15 slide phải nối với nhau như một cuộc điều tra:
  symptom -> confusion -> distributed complexity -> refresher -> core claim -> tracing value -> investigation workflow -> architecture -> signals -> scenario -> expected evidence -> takeaway -> demo bridge

Không được làm các việc sau:
- không thêm slide lịch sử Prometheus, Tempo, Grafana
- không thêm slide định nghĩa dài về logs/metrics/traces
- không dùng bảng chữ dày đặc
- không dùng icon server/cloud/database/robot/shield/magnifying glass
- không thêm quote truyền cảm hứng
- không dùng cấu trúc pitch deck kiểu "problem / solution / benefits"
- không sinh thêm slide ngoài 15 slide được chỉ định
- không đổi thứ tự 15 slide

Hãy tạo đúng 15 slide theo đặc tả sau:

Slide 1
Headline:
"Healthy Does Not Mean Correct"
Mục tiêu:
- định vị ngay hướng tiếp cận khác biệt của nhóm
Visual chính:
- sơ đồ hệ thống trừu tượng nhiều tầng, trong đó hạ tầng còn xanh nhưng luồng giá trị bị nghẽn hoặc sai
Text trên slide:
- chỉ title
- subtitle rất ngắn
- tên nhóm

Slide 2
Headline:
"Hệ thống vẫn sống, nhưng kết quả đã sai"
Mục tiêu:
- mở bằng nghịch lý kỹ thuật chứ không mở bằng định nghĩa
Visual chính:
- split-screen hoặc before/after:
  bên trái "API up / dashboard green"
  bên phải "data stale / business flow degraded"
Text trên slide:
- rất ít
- chỉ vài nhãn ngắn

Slide 3
Headline:
"Vì sao microservices khó debug hơn?"
Mục tiêu:
- cho thấy symptom và root cause không ở cùng một nơi
Visual chính:
- một request flow đi qua nhiều service và dependency:
  User -> API -> Service -> Queue -> Processor -> Storage -> Dashboard
- điểm lỗi nằm giữa luồng nhưng triệu chứng xuất hiện ở cuối

Slide 4
Headline:
"Nhắc lại rất nhanh: observability là gì?"
Mục tiêu:
- nhắc nền tảng đủ dùng, không dạy lại từ đầu
Visual chính:
- một "black box system" ở giữa, xung quanh là output signals
Text trên slide:
- chỉ 1 câu cực ngắn về khả năng suy ra trạng thái bên trong từ telemetry bên ngoài

Slide 5
Headline:
"Trace, Span, Trace ID"
Mục tiêu:
- giữ phần lý thuyết bắt buộc nhưng bằng hình, không bằng text dài
Visual chính:
- trace waterfall hoặc span tree đơn giản:
  API -> service -> DB / external dependency
Text trên slide:
- chỉ các nhãn ngắn:
  trace
  span
  trace id
  parent-child

Slide 6
Headline:
"Monitoring thấy bất thường. Observability giải thích bất thường."
Mục tiêu:
- chuyển từ refresher sang tư duy điều tra
Visual chính:
- comparison visual hoặc 2-lane diagram
- không dùng bảng text dài
Text trên slide:
- chỉ hai câu rất ngắn:
  monitoring = biết có vấn đề
  observability = biết vì sao có vấn đề

Slide 7
Headline:
"Healthy does not mean correct"
Mục tiêu:
- đây là luận điểm trung tâm của cả bài
Visual chính:
- một health check màu xanh ở API,
  nhưng nhánh pipeline dữ liệu ở giữa bị đỏ hoặc ngắt
Text trên slide:
- cực ít
- nhấn mạnh:
  health pass
  business flow degraded

Slide 8
Headline:
"Tracing quan trọng vì lỗi thường không ở nơi ta nhìn thấy"
Mục tiêu:
- giải thích vai trò tracing trong distributed systems
Visual chính:
- trace waterfall với một span kéo dài nổi bật
- cho thấy bottleneck nằm ở downstream hoặc dependency
Text trên slide:
- chỉ 2-3 nhãn ngắn

Slide 9
Headline:
"Quy trình điều tra sự cố"
Mục tiêu:
- cho thấy observability là workflow, không phải bộ công cụ rời rạc
Visual chính:
- incident investigation pipeline:
  metrics -> traces -> logs -> root cause
Text trên slide:
- càng ít càng tốt

Slide 10
Headline:
"Kiến trúc demo của nhóm"
Mục tiêu:
- gắn bài nói với hệ thống thật
Visual chính:
- sơ đồ 2 lớp
  lớp 1: business data flow
    GitHub Events API -> Poller -> Kafka -> Spark -> ClickHouse/Parquet -> FastAPI -> Frontend
  lớp 2: observability flow
    Prometheus <- metrics
    Tempo <- traces
    Grafana <- unified analysis
Lưu ý:
- đây là slide kiến trúc quan trọng nhất, phải rõ và đẹp

Slide 11
Headline:
"Nhóm quan sát những tín hiệu nào?"
Mục tiêu:
- gắn lý thuyết với các signal thật trong demo
Visual chính:
- layered signal map hoặc grouped diagram
Nội dung cần xuất hiện bằng nhãn ngắn:
- metrics:
  latency
  request rate
  data freshness
  throughput
  processor health
- tracing:
  request path
  outbound call
  X-Trace-Id
- operational signals:
  health
  lag
  staleness

Slide 12
Headline:
"Kịch bản demo: API vẫn sống, nhưng pipeline bị stale"
Mục tiêu:
- công bố rõ incident mà nhóm sẽ demo
Visual chính:
- timeline hoặc pipeline diagram với điểm đứt/chậm ở processor
Text trên slide:
- rất ít
- phải thể hiện:
  processor dừng hoặc chậm nặng
  API vẫn trả lời
  dữ liệu mới không đi xuyên pipeline như bình thường

Slide 13
Headline:
"Dấu hiệu kỳ vọng khi sự cố xảy ra"
Mục tiêu:
- biến demo thành kiểm chứng có mục tiêu
Visual chính:
- before/after abstraction:
  throughput down
  freshness up
  latency spike
  trace evidence
Lưu ý:
- không chụp screenshot thật
- dùng visual abstraction mô phỏng panel và trace

Slide 14
Headline:
"Giá trị kỹ thuật rút ra"
Mục tiêu:
- chốt bài bằng insight kỹ thuật, không chốt bằng mô tả tool
Visual chính:
- flow cuối:
  symptom -> evidence -> root cause -> fix decision
Text trên slide:
- observability không chỉ để nhìn
- observability để truy nguyên
- giảm đoán mò
- giảm MTTR

Slide 15
Headline:
"Chuyển sang demo live"
Mục tiêu:
- nối mượt sang phần demo 11 phút
Visual chính:
- investigation checklist hoặc step-by-step board
Text trên slide:
- rất ít
- chỉ nhắc khán giả chú ý:
  API still up
  metrics drift
  trace drilldown
  root cause reveal

Ràng buộc đầu ra:
- toàn bộ nội dung slide phải bằng tiếng Việt
- text trên slide phải ngắn
- ưu tiên nhãn ngắn hơn bullet
- không dùng icon ở bất kỳ slide nào
- không dùng hình minh họa generic
- không làm lệch trọng tâm sang "giới thiệu Prometheus/Tempo/Grafana"
- phải giữ nguyên tinh thần: đây là deck điều tra sự cố trong microservices

Nếu phải chọn giữa "đẹp" và "đúng cấu trúc":
- ưu tiên đúng cấu trúc
```

## 8.3 Gamma AI Short Prompt

Nếu Gamma phản hồi tốt hơn với prompt ngắn hơn, dùng bản rút gọn này nhưng vẫn giữ đủ độ chặt:

```text
Tạo deck seminar kỹ thuật 15 slide bằng tiếng Việt với chủ đề:
"Healthy Does Not Mean Correct"

Đây KHÔNG phải là deck giới thiệu observability chung chung.
Đây là deck điều tra sự cố trong microservices.

Luận điểm trung tâm:
- API có thể vẫn trả 200 OK
- dashboard vẫn có thể còn xanh
- nhưng business flow đã sai hoặc stale
- observability có giá trị vì giúp tìm root cause nhanh

Ngữ cảnh demo thật:
- GitHub Events API -> Poller -> Kafka -> Spark -> ClickHouse + Parquet -> FastAPI -> Next.js
- Prometheus = metrics
- Tempo = tracing backend
- Grafana = unified investigation UI
- Có X-Trace-Id và X-Trace-Explore-Url để correlation

Thiết kế bắt buộc:
- đúng 15 slide
- mỗi slide 1 headline mạnh
- mỗi slide 1 visual chính
- rất ít chữ
- nhiều architecture diagram, service flow, observability flow, incident timeline, trace waterfall
- không icon
- không emoji
- không stock image
- không layout marketing
- không bảng nhiều chữ

Flow bắt buộc của 15 slide:
1. Title
2. Opening paradox: system alive but wrong
3. Why microservices are hard to debug
4. Very short refresher: observability
5. Visual refresher: trace/span/trace ID
6. Monitoring vs observability
7. Healthy does not mean correct
8. Why tracing matters
9. Incident investigation workflow
10. Demo architecture with business flow + observability flow
11. Signals observed in the system
12. Demo scenario
13. Expected evidence during incident
14. Technical takeaway
15. Transition to live demo

Ngôn ngữ trên slide:
- ngắn
- kỹ thuật
- nghiêm túc
- học thuật vừa đủ

Ưu tiên tuyệt đối:
- đúng cấu trúc
- đúng narrative
- visual-first
```

## 9. Questions The Lecturer May Ask

### Câu hỏi 1

`Observability khác gì monitoring?`

**Trả lời ngắn**

> Monitoring chủ yếu theo dõi những tín hiệu đã biết trước và cảnh báo khi vượt ngưỡng.
> Observability cho phép suy ra trạng thái bên trong hệ thống từ telemetry để điều tra cả
> những tình huống chưa dự đoán trước.

### Câu hỏi 2

`Nếu đã có log thì cần tracing làm gì?`

**Trả lời ngắn**

> Log cho biết chi tiết một sự kiện cục bộ. Tracing cho biết quan hệ nhân quả xuyên service.
> Trong hệ nhiều service, chỉ có log thì rất khó ghép đúng toàn bộ hành trình của một request.

### Câu hỏi 3

`Hệ nhỏ có cần observability phức tạp như vậy không?`

**Trả lời ngắn**

> Không phải lúc nào cũng cần mức độ đầy đủ như hệ lớn. Nhưng khi hệ thống có nhiều thành phần,
> nhiều điểm gọi nhau hoặc có xử lý bất đồng bộ, observability trở nên rất quan trọng để giảm
> thời gian truy lỗi.

### Câu hỏi 4

`Tại sao API còn sống mà vẫn coi là lỗi?`

**Trả lời ngắn**

> Vì availability của một endpoint không đồng nghĩa với correctness của toàn bộ business flow.
> Nếu dữ liệu không còn được xử lý hoặc không còn cập nhật, hệ thống vẫn đang mất giá trị vận hành.

## 10. Risks And Mitigations

### Risk

Phần lý thuyết bị đánh giá là lặp lại.

### Mitigation

- giữ khái niệm đủ chắc nhưng cô đọng
- chuyển nhanh sang insight và incident workflow

### Risk

Demo không khớp với phần trình bày.

### Mitigation

- slide 12 và 13 phải nêu rõ scenario và expected signals

### Risk

Người nghe thấy nhóm chỉ đang giới thiệu tool.

### Mitigation

- luôn nhấn vào câu hỏi:
  - vấn đề là gì
  - observability phát hiện gì
  - tracing truy nguyên gì

## 11. Definition Of Done For The Presentation Package

Phần nội dung được coi là sẵn sàng khi:

- có đủ `15 slide`
- mỗi slide có 1 headline rõ
- mỗi người nắm phần của mình dưới `5 phút`
- có câu nối mượt từ slide 15 sang demo
- có sẵn 3-4 câu trả lời phản biện ngắn
- toàn bộ phần trình bày không lặp lại quá nhiều so với 2 nhóm trước

## 12. Next Deliverables

Sau tài liệu này, nhóm nên làm tiếp theo thứ tự:

1. chốt visual theme cho slide
2. viết script nói cho từng người theo từng slide
3. chuẩn bị asset hình:
   - trace flow
   - kiến trúc hệ thống
   - incident workflow
4. tập thử đúng thời gian `14 phút`
5. sau đó mới khóa runbook cho `11 phút` demo
