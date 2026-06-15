FROM python:3.14-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:0.7.13 /uv /uvx /bin/

# Install Java for PySpark.
RUN apt-get update && apt-get install -y --no-install-recommends \
    openjdk-17-jre-headless \
    procps \
    wget \
    && rm -rf /var/lib/apt/lists/*

ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ENV PATH="${JAVA_HOME}/bin:${PATH}"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_LINK_MODE=copy

WORKDIR /app

# Install dependencies once; source code is bind-mounted at runtime.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --extra dev --no-install-project

EXPOSE 8000 9091

CMD ["uv", "run", "uvicorn", "src.presentation.api.routes:app", "--host", "0.0.0.0", "--port", "8000"]
