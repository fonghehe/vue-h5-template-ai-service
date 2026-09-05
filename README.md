# vue-h5-template-ai-service

[English](./README.md) · [简体中文](./README.zh-CN.md) · [日本語](./README.ja.md)

FastAPI AI assistant backend for [vue-h5-template](https://github.com/fonghehe/vue-h5-template). It preserves `POST /api/ai/chat` and the `@vh5/ai-chat` SSE contract, and adds user-owned conversations, bounded context, registered tools, optional LangGraph agent flow, PostgreSQL/pgvector knowledge retrieval, and usage/observability endpoints.

This is a Python service, not a Vue frontend. The sibling Go business service issues JWTs and owns product CRUD; this service can call its product API through a fixed, registered tool. The default mock model works offline and is not a measure of real-model quality.

## Quick start

```bash
cp .env.example .env
uv sync --dev
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

## License

[MIT](./LICENSE)
