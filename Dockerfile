# syntax=docker/dockerfile:1
# An existing image with the same frozen dependencies can seed an offline build.
ARG PYTHON_BUILD_IMAGE=python:3.13-slim
FROM ${PYTHON_BUILD_IMAGE} AS builder
USER root
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
RUN pip install --no-cache-dir uv==0.12.9
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
RUN --mount=type=cache,target=/root/.cache/uv \
    UV_HTTP_TIMEOUT=120 UV_HTTP_RETRIES=5 UV_CONCURRENT_DOWNLOADS=4 uv sync --frozen --no-dev --no-install-project

FROM python:3.13-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PATH="/app/.venv/bin:$PATH"
RUN addgroup --system app && adduser --system --ingroup app app
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini
RUN mkdir -p /app/.data && chown app:app /app/.data
USER app
EXPOSE 8001
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8001/health', timeout=2)" || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001", "--timeout-graceful-shutdown", "100"]
