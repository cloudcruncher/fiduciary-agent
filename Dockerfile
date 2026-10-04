# syntax=docker/dockerfile:1
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY fiduciary/ fiduciary/
COPY litellm_config.yaml README.md LICENSE ./
RUN uv sync --frozen --no-dev

FROM python:3.12-slim-bookworm

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/fiduciary /app/fiduciary
COPY --from=builder /app/litellm_config.yaml /app/litellm_config.yaml
COPY --from=builder /app/README.md /app/LICENSE /app/

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV FIDUCIARY_DATA_DIR="/app/data"

RUN mkdir -p /app/data
VOLUME ["/app/data"]

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/ || exit 1

CMD ["uvicorn", "fiduciary.web.app:app", "--host", "0.0.0.0", "--port", "8080"]
