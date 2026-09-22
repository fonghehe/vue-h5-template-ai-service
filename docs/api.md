# API reference

Base URL is the AI service (local `http://localhost:8001`). JSON success and pre-stream errors use `{ "code": 0, "message": "ok", "data": ..., "error": null, "requestId": "..." }`; nonzero `code` represents failure. SSE uses JSON `data:` frames instead of this envelope. `X-Request-ID` is returned in headers. `/docs` and `/openapi.json` exist only when `DOCS_ENABLED=true`.

| Method | Path | Principal | Response |
| --- | --- | --- | --- |
| GET | `/health` | public | process liveness envelope |
| GET | `/ready` | public | limiter readiness envelope, 503 if degraded |
| GET | `/metrics` | public if enabled | Prometheus exposition, otherwise 404 |
| GET | `/api/ai/suggestions` | — | JSON `string[]` |
| POST | `/api/ai/chat` | user/service/anonymous when allowed | legacy SSE, no persistence |
| POST, GET | `/api/conversations` | user JWT | create/list |
| GET, DELETE | `/api/conversations/{id}` | owner JWT | details/delete |
| POST | `/api/conversations/{id}/messages` | owner JWT | persistent SSE |
| POST, GET | `/api/knowledge/documents` | user JWT | upload/list |
| DELETE | `/api/knowledge/documents/{id}` | owner JWT | delete |
| GET | `/api/usage/me` | user JWT | totals and breakdowns |

## Legacy chat

```bash
curl -N http://localhost:8001/api/ai/chat -H 'Content-Type: application/json' -d '{"messages":[{"role":"user","content":"Hello"}]}'
```

Body requires `messages` (1–100 entries) and optional `conversationId` (maximum 120 characters). Each message has `role` (`system`, `user`, `assistant`, `tool`), `content` (maximum 20,000 characters), optional `id`, `createdAt`, `toolCalls`, `toolCallId`. A `tool` message requires `toolCallId`; empty content requires tool calls. Combined content is capped at 100,000 characters. This route trusts the supplied history within validation limits and does not save it. See [SSE](/sse).

## Conversations

```bash
curl -s http://localhost:8001/api/conversations -H "Authorization: Bearer $AI_USER_JWT" -H 'Content-Type: application/json' -d '{"title":"Shopping help"}'
curl -N "http://localhost:8001/api/conversations/$AI_CONVERSATION_ID/messages" -H "Authorization: Bearer $AI_USER_JWT" -H 'Content-Type: application/json' -d '{"content":"Find products under 500","mode":"agent","useRag":false}'
```

Create accepts optional `title` (default `New conversation`) and `model` (must match a configured model). Message body requires `content` (1–100,000 characters) and accepts `mode: "auto" | "chat" | "agent"`, `useRag: boolean`. The response is SSE. Detail returns `id`, `userId`, `title`, `model`, `summary`, `createdAt`, `updatedAt`, `messages`. Message objects include `id`, `conversationId`, `role`, `content`, `toolCallId`, `tokenUsage`, `latencyMs`, `citations`, `createdAt`. List omits `messages`. See [Conversations](/conversations).

## Knowledge and usage

```bash
curl -s http://localhost:8001/api/knowledge/documents -H "Authorization: Bearer $AI_USER_JWT" -F 'file=@notes.md' -F 'metadata={"topic":"catalog"}'
curl -s http://localhost:8001/api/usage/me -H "Authorization: Bearer $AI_USER_JWT"
```

Upload supports `.txt`, `.md`, `.pdf`; `metadata` is a JSON object encoded as a form string, default `{}`. The document view returns `id`, `title`, `source`, `metadata`, `createdAt`. List and delete are owner-scoped. Usage returns `promptTokens`, `completionTokens`, `totalTokens`, `requests` and `byModel`, `byConversation`, `byDate` breakdowns. Legacy chat is excluded.

## Error codes and limits

| Code | HTTP | Meaning |
| --- | --- | --- |
| 4000 / 4001 | 400 / 422 | bad request / Pydantic validation |
| 4010 / 4030 / 4040 | 401 / 403 / 404 | authentication / ownership / missing resource |
| 4090 / 4290 | 409 / 429 | conflict / quota |
| 5000 / 5030 | 500 / 502 | internal / provider unavailable |

`/health` is process liveness and exposes backend names only. `/ready` concurrently checks Redis/limiter and the database with bounded timeouts and returns 503 on errors; it does not call a model or the Go service. Redis coordination errors fail closed with a safe 503 envelope. `/metrics` must be restricted at the proxy/network layer. `OTEL_ENABLED` installs tracing hooks without an exporter.

Collections accept `page` (1–100000) and `page_size` (1–100, default 50), preserving the existing list envelope. Conversation details return the latest 100 messages by default; use `page_size` and `before=<sequence>` for earlier pages. Message responses expose `sequence`. Context loads at most 200 recent messages, bounds summarization input, and preserves the newest user turn or rejects it if too large. Persistent message content is limited to 20000 characters and the configured context budget. Old `/api/*` paths remain; every business route also has an `/api/v1/*` alias.

## Starter prompt API

`GET /api/ai/suggestions` is public and returns three curated strings in the standard JSON envelope. It does not call a model, use model keys, spend model tokens, write conversation history or consume a streaming admission lease. `/api/v1/ai/suggestions` is an equivalent alias. It is not an SSE endpoint.

`locale` is optional and accepts exactly `en-US`, `zh-CN`, or `ja-JP`; the default is `en-US`. Unsupported values, including `zh-TW`, return HTTP 422 with application code 4001. The frontend normalizes its locale before requesting. `Accept-Language` does not select this endpoint’s language.

```bash
curl -s 'http://localhost:8001/api/ai/suggestions'
curl -s 'http://localhost:8001/api/v1/ai/suggestions?locale=ja-JP'
```

```json
{
  "code": 0,
  "message": "ok",
  "data": [
    "Help me compare products before buying.",
    "What should I check before placing an order?",
    "Explain how streaming AI responses work."
  ],
  "error": null,
  "requestId": "example-request-id"
}
```

Curated text lives in `app/services/suggestions.py`; HTTP validation and response wrapping live in `app/api/v1/suggestions.py`. Edit each language deliberately and keep the Literal contract, frontend OpenAPI enum and tests synchronized when adding a locale. The service returns a new list so a caller cannot mutate the shared prompt tuple. It does not personalize prompts from user history.

[Tests](./extending.md)
