# Observability Stack

This folder contains the local monitoring, logging, tracing, and Grafana provisioning for
GitHub AI Analyzer.

## Services

| Service | URL | Purpose |
| --- | --- | --- |
| Grafana | http://localhost:3001 | Dashboards and Explore UI |
| Prometheus | http://localhost:9093 | Metrics storage and PromQL |
| Loki | http://localhost:3100 | Container log storage |
| Tempo | http://localhost:3200 | Trace storage and lookup |

## Data Sources

Grafana provisions these stable datasource UIDs:

- `prometheus_ds`: Prometheus at `http://prometheus:9090`
- `clickhouse_ds`: ClickHouse HTTP at `http://clickhouse:8123`
- `loki_ds`: Loki at `http://loki:3100`
- `tempo_ds`: Tempo at `http://tempo:3200`

Dashboards should reference these UIDs directly. Avoid using generated datasource names because
they are harder to keep stable across local rebuilds.

## Metrics Contract

The API metrics server listens on `METRICS_PORT`, default `9091`, inside the API container.
Prometheus scrapes it through the `github_analyzer_api` job.

Core metrics:

- `api_requests_total{method,route,status_code}`
- `api_request_duration_seconds_bucket{method,route,status_code}`
- `api_in_flight_requests`
- `data_freshness_seconds`
- `pipeline_status{status}`
- `ai_requests_total{endpoint,status}`
- `ai_request_duration_seconds_bucket{endpoint,status}`

## Dashboards

- `GHA API & Pipeline Overview`: request rate, error rate, latency, freshness, and pipeline state.
- `GHA ClickHouse Data Overview`: direct ClickHouse views over `github_data`.
- `GHA Silent Failure Demo`: shows how the API can stay healthy while data freshness degrades.

## Debug Flow

1. Start the stack:

   ```bash
   cp .env.example .env
   docker compose up --build
   ```

2. Call the API:

   ```bash
   curl -i http://localhost:8000/health
   curl -i http://localhost:8000/pipeline/status
   ```

3. Check response headers:

   - `X-Request-Id`
   - `X-Trace-Id`
   - `X-Trace-Explore-Url`

4. Open `X-Trace-Explore-Url` in Grafana to inspect the Tempo trace.

5. From the trace, pivot to Loki logs and Prometheus metrics.

## Local Notes

- If `docker compose config` fails because `.env` is missing, create it from `.env.example`.
- Promtail needs access to Docker container logs, so Docker Desktop or the Docker Engine must expose
  `/var/run/docker.sock` and `/var/lib/docker/containers`.
- ClickHouse dashboard panels assume the `github_data` table exists.

## Provisioning Checks

Use these checks after changing dashboards or datasources:

```bash
python -c "import json, pathlib; [json.loads(p.read_text()) for p in pathlib.Path('observability/grafana_provisioning/dashboards').glob('*.json')]"
python -c "import yaml, pathlib; [yaml.safe_load(p.read_text()) for p in pathlib.Path('observability').glob('*.yml')]"
docker compose config
```

`docker compose config` requires a local `.env`; create it from `.env.example` for local validation.
