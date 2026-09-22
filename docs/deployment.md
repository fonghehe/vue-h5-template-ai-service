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

`/health` is process liveness and exposes backend names only. `/ready` concurrently checks Redis/limiter and the database with bounded timeouts and returns 503 on errors; it does not call a model or the Go service. Redis coordination errors fail closed with a safe 503 envelope. `/metrics` must be restricted at the proxy/network layer. `OTEL_ENABLED` installs tracing hooks without an exporter.

## CI and docs site

`.github/workflows/ci.yml` runs ruff, strict mypy, pytest with coverage and Docker build. `.github/workflows/deploy-docs.yml` runs `npm ci`, docs type-check/build and GitHub Pages deployment on main docs changes. Production VitePress base is `/vue-h5-template-ai-service/`; local dev uses `/`. See [Configuration](/configuration).


## Operating the service

Register schema changes with Alembic. The initial revision supports PostgreSQL/pgvector and SQLite, and the additive `20261002_0002` revision aligns ORM indexes. Upgrade before traffic; do not run competing migrations in every production replica. Use `alembic check` in CI to detect drift. Back up data before production upgrades; `downgrade base` is only a disposable-test operation.

The default stream deadline is 90 seconds. Set Uvicorn graceful shutdown to at least deadline + 10 seconds and container stop grace to another 10 seconds. Compose uses `exec uvicorn` so SIGTERM reaches the server. For a changed deadline, adjust both grace periods.

Trust forwarded headers only from your ingress IP/CIDR, for example `--proxy-headers --forwarded-allow-ips=10.0.0.10`; never blindly trust client-supplied X-Forwarded-For. Restrict direct service access to the ingress. Apply these proxy settings to legacy and versioned chat routes:

```nginx
location /api/ {
    proxy_pass http://ai:8001;
    proxy_http_version 1.1;
    proxy_buffering off;
    proxy_read_timeout 120s;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $remote_addr;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

The read timeout must exceed your heartbeat interval. Terminate TLS and allow only configured origins/hosts. Keep `/metrics` private. HTTP metrics include count, status, full response duration and active requests; route templates prevent cardinality growth from conversation IDs. Logs include service, environment and request ID; outbound provider/tool calls forward X-Request-ID without exposing credentials. `/api/usage/me` is approximate completed-turn usage, not a billing ledger.

CI runs real pgvector/Redis integration tests and migration round trips. `make integration` requires a disposable `vh5_ai_test` database and Redis DB 15. Use mocked upstream models; no live credentials are needed. Dependency audit command:

```bash
uv export --frozen --no-dev --no-emit-project --no-hashes -o /tmp/ai-requirements.txt
uvx --from pip-audit==2.10.1 pip-audit --no-deps --disable-pip -r /tmp/ai-requirements.txt
```
