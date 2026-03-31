# Contributing

## Quy ước làm việc

- Tách commit nhỏ, có chủ đích, theo Conventional Commits.
- Không commit `.env`, dữ liệu trong `data/`, cache Python, `node_modules/` hoặc `.next/`.
- Chạy `make lint`, `make type-check`, `make test` trước khi push backend changes.
- Chạy `npm --prefix frontend run lint` và `npm --prefix frontend run type-check` trước khi push
  thay đổi frontend.

## Quy trình đề xuất

1. Tạo branch mới từ `main`.
2. Copy `.env.example` thành `.env` và điền biến cần thiết.
3. Cài toolchain bằng `make install-dev` và `make frontend-install`.
4. Commit theo từng thay đổi độc lập.
5. Mở pull request kèm mô tả scope và cách verify.

## Docker

- `docker compose up --build` để chạy stack chuẩn.
- `docker compose --profile ai up --build` nếu cần bật Ollama.
- Nếu module FastAPI entrypoint thay đổi, override `APP_MODULE` trong môi trường compose.

