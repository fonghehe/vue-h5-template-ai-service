# syntax=docker/dockerfile:1

# ---------------------------------------------------------------------------
# Runtime image. Dependencies are installed with uv from the frozen lockfile,
# the application is copied as a plain package directory, and the container
# runs as a non-root user.
# ---------------------------------------------------------------------------
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

RUN pip install --no-cache-dir uv \
    && addgroup --system app \
    && adduser --system --ingroup app app

WORKDIR /app

# Install dependencies first so the layer is cached when only app/ changes.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini

# Keep the development fallback writable when the image is run without the
# production PostgreSQL environment. Compose/production use PostgreSQL.
RUN mkdir -p /app/.data && chown -R app:app /app/.data

ENV PATH="/app/.venv/bin:$PATH"

USER app
EXPOSE 8001

HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8001/health', timeout=2)" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
