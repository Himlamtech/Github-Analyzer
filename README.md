# GitHub AI Analyzer

Backend FastAPI + frontend Next.js cho phân tích xu hướng GitHub, AI search, ClickHouse và observability
với Grafana, Loki, Promtail, Tempo.

## Thành phần chính

- `src/`: backend Python theo hướng layered architecture.
- `tests/`: backend test suite.
- `frontend/`: dashboard Next.js.
- `observability/`: cấu hình Loki, Tempo, Promtail và provisioning Grafana.
- `scripts/`: tiện ích vận hành và backfill.

## Yêu cầu

- Python `3.12`
- Node.js `20`
- Docker và Docker Compose plugin

## Khởi tạo local

1. Tạo file môi trường:

   ```bash
   cp .env.example .env
   ```

2. Cài backend:

   ```bash
   make install-dev
   ```

3. Cài frontend:

   ```bash
   make frontend-install
   ```

## Chạy local không dùng Docker

Backend:

```bash
uvicorn src.presentation.api.routes:app --reload --host 0.0.0.0 --port 8000
```

Frontend:

```bash
make frontend-dev
```

## Chạy bằng Docker

Stack mặc định:

```bash
docker compose up --build
```

Stack có thêm Ollama:

```bash
docker compose --profile ai up --build
```

## Lệnh thường dùng

```bash
make format
make lint
make type-check
make test
```

## Biến môi trường chính

- `CLICKHOUSE_*`: kết nối ClickHouse.
- `OLLAMA_*`: embedding/generation backend.
- `AI_*`: bật tắt và tinh chỉnh AI endpoints.
- `TRACING_*`: OTLP exporter và sampling.
- `GRAFANA_PASSWORD`: mật khẩu admin Grafana.

## Ghi chú

- Root `.gitignore` đã loại trừ `.env`, `data/`, cache Python, `node_modules/`, `.next/` và các
  local artifact để tránh commit nhầm.
- Compose backend mặc định dùng `APP_MODULE=src.presentation.api.routes:app`. Nếu composition root
  của bạn nằm ở module khác, chỉ cần override biến môi trường này.

