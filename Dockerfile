FROM python:3.11-slim-bookworm

# Install Java for PySpark
RUN apt-get update && apt-get install -y --no-install-recommends \
    openjdk-17-jre-headless \
    wget \
    && rm -rf /var/lib/apt/lists/*

ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ENV PATH="${JAVA_HOME}/bin:${PATH}"

WORKDIR /app

# Copy dependency spec first for layer caching
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e ".[dev]" || pip install --no-cache-dir \
    httpx[http2] tenacity aiokafka orjson pyspark==3.5.1 clickhouse-driver duckdb \
    fastapi uvicorn[standard] pydantic pydantic-settings prometheus-client \
    opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp-proto-http \
    opentelemetry-instrumentation-fastapi opentelemetry-instrumentation-httpx \
    structlog anyio

COPY src/ ./src/

EXPOSE 8000 9091

CMD ["uvicorn", "src.presentation.api.routes:app", "--host", "0.0.0.0", "--port", "8000"]
