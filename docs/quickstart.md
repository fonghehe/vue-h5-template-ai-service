# Quick start

## Requirements

Python 3.12–3.14 and `uv` run the API. Node.js and npm are needed only to work on the VitePress site. The root is a Python project (`pyproject.toml` + `uv.lock`); only `docs/` has `package.json` and `package-lock.json`. There is no pnpm script at the repository root.

## Offline local run

```bash
cp .env.example .env
uv sync --dev
uv run uvicorn app.main:app --reload --port 8001
```

Defaults use the mock provider and a local SQLite file at `.data/ai-service.db`; schema is created on startup. This is a development fallback, not the production PostgreSQL/pgvector deployment. Open `http://localhost:8001/docs` while `DOCS_ENABLED=true`.

```bash
curl -N http://localhost:8001/api/ai/chat \
  -H 'Content-Type: application/json' \
  -d '{"messages":[{"role":"user","content":"Hello"}]}'
```

The response is `data: {"type":"start",...}`, zero or more `delta` frames, then `finish`. The mock's answer is a canned explanation, not an answer to the question.

## Persistent conversations

These endpoints require a **user JWT** minted by the Go business service, even when `AI_AUTH_REQUIRED=false`. A `SERVICE_TOKEN` cannot access user-owned conversations. With a valid JWT:

```bash
curl -s http://localhost:8001/api/conversations \
  -H "Authorization: Bearer $AI_USER_JWT" \
  -H 'Content-Type: application/json' \
  -d '{"title":"First chat"}'
```

Use the returned `data.id` with `POST /api/conversations/{id}/messages`; see [Conversations](/conversations). The service does not issue JWTs.

## Production-shaped local stack

```bash
docker compose up --build
```

Compose starts the AI API, Redis and PostgreSQL with pgvector, runs `alembic upgrade head`, and publishes the API on `8001`. It sets `AI_AUTH_REQUIRED=true`, so the anonymous chat curl above returns 401 in Compose. The Go business service is **not** included; `search_product` needs that separate service at the configured URL. See [Deployment](/deployment).

## Verification and docs

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy app
cd docs
npm ci
npm run docs:dev
npm run docs:build
```

The docs dev server is a separate VitePress process; it does not start the API. CI additionally builds the Docker image. Continue with [Configuration](/configuration).
