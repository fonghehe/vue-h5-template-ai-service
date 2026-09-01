# Deployment

## Build the image

```bash
docker build -t vue-h5-template-ai-service:latest .
# or
make docker
```

The image runs as a **non-root** user and includes a container health check.

## Run with docker compose

```bash
cp .env.example .env
docker compose up --build
```

This starts the service plus a Redis 7 instance (for multi-instance rate limiting). The API listens on
`http://localhost:8001`.

## Streaming-specific notes

SSE is sensitive to proxy buffering. When fronting the service with nginx or an equivalent:

```nginx
location /api/ai/chat {
    proxy_buffering off;
    proxy_cache off;
    proxy_read_timeout 300s;
    proxy_http_version 1.1;
}
```

The service already sends `X-Accel-Buffering: no` and `Cache-Control: no-cache, no-transform` to stop
intermediaries from buffering or recompressing the stream.

## Production checklist

- **Set `SERVICE_TOKEN`** and rotate it with the gateway.
- **Replace `JWT_SECRET`** — and keep it identical to the business service.
- **Set `AI_AUTH_REQUIRED=true`** before exposing the service publicly.
- **Use `AI_PROVIDER=openai-compatible`** with a real `AI_API_KEY`.
- **Set `REDIS_URL`** when running more than one replica — otherwise each replica keeps its own quota.
- **Terminate TLS upstream** and set `CORS_ORIGINS` to real domains.
- **Set `DOCS_ENABLED=false`** in production.

## CI

GitHub Actions runs on every PR and push to `main`: `ruff check`, `ruff format --check`, `mypy app`, `pytest` with
coverage, and a Docker image build.
