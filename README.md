# vue-h5-template-ai-service

[English](./README.md) · [简体中文](./README.zh-CN.md) · [日本語](./README.ja.md)

FastAPI AI backend for [vue-h5-template](https://github.com/fonghehe/vue-h5-template): incremental SSE chat, saved conversations, registered tools and document retrieval (RAG). The sibling Go service issues JWTs and provides product APIs.

## Run locally

Requires Python 3.12–3.14 and uv. Defaults use SQLite and an offline mock model; they need no model key. Run curl from another terminal.

```bash
cp .env.example .env
uv sync --frozen --dev
uv run uvicorn app.main:app --reload --port 8001
```

```bash
curl -N http://localhost:8001/api/ai/chat \
  -H 'Content-Type: application/json' \
  -d '{"messages":[{"role":"user","content":"Hello"}]}'
```

Persistent conversations and knowledge endpoints require a Go-issued user access JWT even in local mode. Mock tests do not establish real model quality or production capacity.

## Read next

- [Local setup](./docs/quickstart.md)
- [API and authentication](./docs/api.md)
- [Streaming contract](./docs/sse.md)
- [Configuration](./docs/configuration.md)
- [Deployment](./docs/deployment.md)
- [Development and tests](./docs/contributing.md)

[VitePress](https://fonghehe.github.io/vue-h5-template-ai-service/) · [MIT](./LICENSE)
