# Deployment

## Local container stack

`docker compose up --build` starts the API on `127.0.0.1:8001`, Redis 7 and PostgreSQL 17/pgvector. It runs migrations before Uvicorn, uses the mock model and requires chat authentication. Its credentials are local examples. The Go service is separate; `host.docker.internal:8002` assumes Docker Desktop or equivalent host mapping.

## Production startup

1. Provision PostgreSQL/pgvector and Redis; configure secrets through your deployment environment.
2. Set staging/production settings from [Configuration](./configuration.md), including `DATABASE_AUTO_CREATE=false`. Match Go’s JWT secret, issuer and audience. Configure the real provider if required.
3. Back up existing data and run migrations once before starting replicas. Do not run competing migrations in every replica.
4. Start the service and check `/health` and `/ready`. Test the target Go product API’s service-token and `X-User-ID` policy separately.

```bash
uv run alembic upgrade head
uv run alembic check
uv run uvicorn app.main:app --host 0.0.0.0 --port 8001 --timeout-graceful-shutdown 100
```

## Proxy and shutdown

Terminate TLS at the ingress. Disable buffering for legacy and `/api/v1` chat routes. The example below covers both; choose a read timeout longer than the heartbeat interval. Trust forwarded headers only from your ingress IP/CIDR, for example `--proxy-headers --forwarded-allow-ips=10.0.0.10`, and restrict direct API access.

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

Keep Uvicorn’s shutdown grace at least 10 seconds above the stream deadline and the container stop grace another 10 seconds longer. Defaults are 90 / 100 / 110 seconds. Update all three together. Compose uses `exec uvicorn` so the server receives SIGTERM.

## Probes and observability

| Endpoint | Meaning |
|---|---|
| `/health` | Process liveness; does not establish dependency health. |
| `/ready` | Bounded concurrent database and limiter probes; failures return 503. Does not call a model or Go. |
| `/metrics` | Prometheus metrics when enabled; restrict at the proxy/network layer. |

HTTP metrics use route templates and standard methods; other methods share `OTHER`. Logs include request IDs, and provider/tool requests forward `X-Request-ID`. Exception logs retain types and stack locations but omit exception values and chained messages. Log messages and extra fields must still avoid secrets.

`OTEL_ENABLED` configures tracing without an exporter. Integrate an exporter and sampling policy with your observability stack; turning on the setting alone does not export traces.

## Operational limits

- Daily usage is an estimate of completed persistent turns, not billing; concurrent requests can exceed the admission threshold.
- PDF parsing uses bounded worker threads, not process isolation. Untrusted large-scale uploads need a resource-limited parser process or worker.
- Default pools and limits are starting settings, not measured production capacity. Validate model, Go, proxy disconnects, backups and rolling shutdown in your target environment.

For isolated integration tests, migration checks and local benchmarks, see [Contributing](./contributing.md).
