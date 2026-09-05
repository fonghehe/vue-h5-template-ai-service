# Deployment

## Local production-shaped stack

```bash
docker build -t vue-h5-template-ai-service:local .
docker compose up --build
```

The non-root image listens on 8001. Compose starts Redis 7, PostgreSQL 17 with pgvector and the API. It runs `alembic upgrade head` before Uvicorn, enables auth and uses the mock model. Its credentials are **development examples**, not production secrets. The Go service is not included; `host.docker.internal:8002` assumes an external sibling process and may need host mapping outside Docker Desktop.

For production, provision PostgreSQL/pgvector and Redis, set `DATABASE_URL=postgresql+asyncpg://...`, `DATABASE_AUTO_CREATE=false`, run `uv run alembic upgrade head` before serving, and keep embedding dimensions compatible with the migration/model. Replace example secrets, set real trusted hosts/CORS, `AI_AUTH_REQUIRED=true`, and match the Go JWT issuer settings. Confirm the receiving product API trusts the service token and `X-User-ID`; this repo alone cannot verify that integration.

## Proxy, probes and observability

Disable proxy buffering for **both** `/api/ai/chat` and `/api/conversations/{id}/messages`, keep a suitable read timeout and terminate TLS. The service already sets `X-Accel-Buffering: no` and `Cache-Control: no-cache, no-transform`.

`/health` is process liveness. `/ready` pings the limiter and returns 503 when degraded; it does **not** probe PostgreSQL, provider or Go service. `/metrics` is unauthenticated when `METRICS_ENABLED=true`; protect it at the proxy/network layer or disable it. `OTEL_ENABLED=true` installs a tracer provider but no exporter. Redis counters coordinate request limits, stream quotas and conversation locks across replicas; Redis failures after startup are not universally handled. `/api/usage/me` counts successfully persisted conversation turns, not billing.

## CI and docs site

`.github/workflows/ci.yml` runs ruff, strict mypy, pytest with coverage and Docker build. `.github/workflows/deploy-docs.yml` runs `npm ci`, docs type-check/build and GitHub Pages deployment on main docs changes. Production VitePress base is `/vue-h5-template-ai-service/`; local dev uses `/`. See [Configuration](/configuration).
