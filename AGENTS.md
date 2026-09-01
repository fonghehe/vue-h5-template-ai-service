# AGENTS.md

This repository owns AI-provider integration and streaming workloads for vue-h5-template. Conventional CRUD and
token issuance belong in the sibling `vue-h5-template-business-service` repository.

## Boundaries

- `app/api`: FastAPI HTTP/SSE boundary only.
- `app/providers`: provider-neutral interfaces and provider adapters.
- `app/services`: rate limiting and supporting services.
- `app/schemas`: validated public contracts.
- `app/core`: configuration, errors, logging, security.
- The SSE protocol is `start`, repeated `delta`, `finish` or `error`.
- Forward cancellation to providers and never buffer a complete model response.
- Never expose model credentials to the Vue client or commit real user data.
- Gin-issued JWT settings must match this service. Redis coordinates rate limits across replicas.

## Commands

```bash
uv sync --dev
uv run ruff check .
uv run ruff format --check .
uv run mypy app
uv run pytest
docker build -t vue-h5-template-ai-service:local .
```

When the stream protocol or the provider contract changes, update the tests and the VitePress docs in `docs/` in
the same change.
