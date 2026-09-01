# vue-h5-template-ai-service

Provider-neutral **streaming AI service** for [vue-h5-template](https://github.com/fonghehe/vue-h5-template).

It accepts a typed list of chat messages and returns a **Server-Sent Events (SSE)** stream that the
`useStreamingChat` composable in `@vh5/ai-chat` consumes directly. Model access sits behind a provider
interface, so the offline mock used in development and a hosted OpenAI-compatible endpoint are
interchangeable without any change to the transport layer or the frontend.

```
Vue H5 app ──POST /api/ai/chat──▶ ai-service ──▶ mock provider   (development)
        ◀── SSE: start/delta/finish ──┘        └─▶ OpenAI-compatible (production)
```

---

## Why a separate service?

| | Business service (Go) | AI service (Python) |
|---|---|---|
| Workload | Short, transactional CRUD | Long-lived streaming connections |
| Scaling | Scale on request rate | Scale on concurrent streams |
| Failure mode | Database latency | Upstream model latency / timeouts |
| Blast radius | A slow model must not exhaust the connection pool | A DB migration must not drop active streams |

Keeping them apart means a slow model provider can never exhaust the connection pool that serves login
and the product catalogue.

---

## Quick start

```bash
# 1. Configure
cp .env.example .env

# 2. Run (uses the offline mock provider — no API key needed)
uv run uvicorn app.main:app --reload --port 8001

# 3. Try it
curl -N http://localhost:8001/api/ai/chat \
  -H 'Content-Type: application/json' \
  -d '{"messages":[{"role":"user","content":"Why is streaming useful?"}]}'
```

```text
data: {"type":"start","id":"conversation-9f2c…"}
data: {"type":"delta","delta":"Streaming "}
data: {"type":"delta","delta":"keeps the UI honest. "}
data: {"type":"finish","reason":"stop"}
```

Interactive docs: <http://localhost:8001/docs>

## Documentation

The documentation is written with VitePress and published to GitHub Pages at
<https://fonghehe.github.io/vue-h5-template-ai-service/>. It is available in three languages —
**English** (primary), **简体中文** and **日本語**:

| Language | URL |
|---|---|
| English | <https://fonghehe.github.io/vue-h5-template-ai-service/> |
| 简体中文 | <https://fonghehe.github.io/vue-h5-template-ai-service/zh/> |
| 日本語 | <https://fonghehe.github.io/vue-h5-template-ai-service/ja/> |

Preview locally:

```bash
cd docs && npm install && npm run docs:dev
```

Publishing is automated: `.github/workflows/deploy-docs.yml` builds and deploys the site whenever `docs/`
changes on `main`.

---

## The SSE contract

Events are exactly the `ChatChunk` union consumed by `@vh5/ai-chat`:

| `type` | Fields | Meaning |
|---|---|---|
| `start` | `id` | Stream accepted; carries the conversation id |
| `delta` | `delta` | One text fragment; concatenate in order |
| `finish` | `reason` | Terminal event: `stop`, `abort` or `error` |
| `error` | `message` | Failure after streaming began; the client throws |

> Errors that happen **before** the first byte are returned as a normal JSON error envelope with
> the proper HTTP status. Errors that happen **during** the stream become an `error` event, because
> the HTTP status has already been sent.

---

## Response envelope

Non-streaming endpoints (including pre-stream errors) use the same envelope as the Go business
service, so the frontend needs only one error handler:

```jsonc
{ "code": 0,     "message": "ok",     "data": { … }, "error": null, "requestId": "…" }
{ "code": 4010,  "message": "Authentication required", "data": null, "error": null, "requestId": "…" }
```

`code === 0` means success — that is the branch `@vh5/api-client` takes.

---

## Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/health` | — | Liveness probe; never touches dependencies |
| `GET` | `/ready` | — | Readiness probe; reports limiter health |
| `POST` | `/api/ai/chat` | optional | Stream a chat completion |

Authentication is off by default so local development needs no setup. Set `AI_AUTH_REQUIRED=true`
to require a JWT minted by the business service, or set `SERVICE_TOKEN` to allow a trusted gateway.

---

## Configuration

Every setting is read from the environment; see [`.env.example`](./.env.example).

| Variable | Default | Notes |
|---|---|---|
| `APP_ENV` | `development` | `development` \| `test` \| `production` |
| `AI_PROVIDER` | `mock` | `mock` \| `openai-compatible` |
| `AI_API_KEY` | — | Required for `openai-compatible` |
| `AI_BASE_URL` | `https://api.openai.com/v1` | Any OpenAI-compatible endpoint |
| `AI_MODEL` | `gpt-4o-mini` | |
| `AI_TIMEOUT_SECONDS` | `60` | 0–300 |
| `AI_RATE_LIMIT_PER_MINUTE` | `20` | Per identity, per minute |
| `AI_AUTH_REQUIRED` | `false` | Require a JWT or service token |
| `JWT_SECRET` | dev placeholder | **Must** match the business service |
| `JWT_ISSUER` / `JWT_AUDIENCE` | `vue-h5-template` / `vue-h5-template-api` | Must match the business service |
| `SERVICE_TOKEN` | — | Shared secret for gateway-to-service calls |
| `REDIS_URL` | — | Empty = in-process limiter |
| `CORS_ORIGINS` | `http://localhost:5173,…` | Comma separated |

Startup refuses unsafe combinations — for example, a default `JWT_SECRET` with `AI_AUTH_REQUIRED=true`,
or `openai-compatible` without an API key — rather than serving broken traffic.

### Swapping providers

Any OpenAI-compatible endpoint works: OpenAI, Azure OpenAI, Together, Groq, Ollama, vLLM.

```bash
AI_PROVIDER=openai-compatible
AI_BASE_URL=https://api.openai.com/v1
AI_API_KEY=sk-…
AI_MODEL=gpt-4o-mini
```

---

## Development

```bash
uv sync                     # install dependencies
make dev                    # run with autoreload
make test                   # pytest with coverage
make lint                   # ruff check + format check
make typecheck              # mypy --strict
make check                  # all of the above
```

---

## Docker

```bash
docker build -t vue-h5-template-ai-service .
docker run --rm -p 8001:8001 --env-file .env vue-h5-template-ai-service
```

The image runs as a non-root user and includes a container health check.

---

## Deployment notes

- **SSE needs unbuffered proxies.** Set `proxy_buffering off;` (nginx) or the equivalent. The service
  also sends `X-Accel-Buffering: no` and `Cache-Control: no-cache, no-transform`.
- **Set `REDIS_URL` when running more than one replica**, otherwise each replica keeps its own quota.
- **Keep `JWT_SECRET` identical** to the business service so tokens minted there validate here.
- **Terminate TLS upstream of the app** and set `CORS_ORIGINS` to real domains in production.

---

## License

[MIT](./LICENSE)
