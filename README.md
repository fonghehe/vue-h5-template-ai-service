# vue-h5-template-ai-service

[English](./README.md) · [简体中文](./README.zh-CN.md) · [日本語](./README.ja.md)

FastAPI AI assistant backend for [vue-h5-template](https://github.com/fonghehe/vue-h5-template). It preserves `POST /api/ai/chat` and the `@vh5/ai-chat` SSE contract, and adds user-owned conversations, bounded context, registered tools, optional LangGraph agent flow, PostgreSQL/pgvector knowledge retrieval, and usage/observability endpoints.

This is a Python service, not a Vue frontend. The sibling Go business service issues JWTs and owns product CRUD; this service can call its product API through a fixed, registered tool. The default mock model works offline and is not a measure of real-model quality.

## Quick start

```bash
cp .env.example .env
uv sync --frozen --dev
uv run uvicorn app.main:app --reload --port 8001
curl -N http://localhost:8001/api/ai/chat -H 'Content-Type: application/json' -d '{"messages":[{"role":"user","content":"Hello"}]}'
```

Defaults use SQLite and the mock provider. For a local PostgreSQL/pgvector + Redis stack, run `docker compose up --build`; Compose requires authentication for chat, while persistent resources specifically require a user JWT. The Go service is separate.

## Documentation

The [developer guide](https://fonghehe.github.io/vue-h5-template-ai-service/) covers architecture, API, SSE, conversations, tools/RAG, configuration, deployment and extension. It is available in [English](https://fonghehe.github.io/vue-h5-template-ai-service/), [简体中文](https://fonghehe.github.io/vue-h5-template-ai-service/zh/) and [日本語](https://fonghehe.github.io/vue-h5-template-ai-service/ja/). The source is in [docs](./docs/index.md).

To run docs locally: `cd docs && npm ci && npm run docs:dev`. This repository has no root pnpm docs script.

## Checks

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy app
cd docs && npm run docs:typecheck && npm run docs:build
```

## Architecture and maintenance

Python 3.12–3.14; uv freezes FastAPI/Pydantic v2, SQLAlchemy 2 async, Alembic, Redis and httpx. HTTP routes call focused services; repositories flush, and services own transactions. Lifespan closes pooled resources even on startup failure. Both `/api/*` and `/api/v1/*` work. See [the audit and implementation plan](./ARCHITECTURE_REVIEW.md) and [verified engineering results](./ENGINEERING_REPORT.md).

## Database and deployment

The local SQLite fallback can auto-create tables. Production uses PostgreSQL/pgvector, Redis and explicit migrations:

```bash
uv run alembic upgrade head
uv run alembic check
curl http://localhost:8001/health
curl http://localhost:8001/ready
```

Set production environment variables before starting; staging/production require authentication, strong secrets, Redis, explicit hosts, JSON logs, disabled docs and `DATABASE_AUTO_CREATE=false`. Run migrations once per deployment before replicas start. The multi-stage image runs as non-root; configure proxy buffering, trusted proxy IPs and a shutdown grace period longer than the stream deadline. Read [deployment](./docs/deployment.md) for concrete settings. JWT issuance remains in the sibling Go service. No user/order/password system is duplicated here.

Tests default to isolated SQLite and mock HTTP/model adapters. Optional PostgreSQL/Redis tests require `AI_TEST_DATABASE_URL` pointing to a disposable `vh5_ai_test` DB and `AI_TEST_REDIS_URL` using DB 15; run `uv run pytest -m integration`. CI supplies these dependencies and verifies migration round trips. Model quality, Go integration, tracing exporters and billing remain explicit operational boundaries.

## License

[MIT](./LICENSE)
