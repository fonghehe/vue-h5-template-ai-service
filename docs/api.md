# API reference

User JWTs must be issued by Go with payload claim `typ: "access"`, in addition to valid HS256 signature, issuer, audience, `exp`, `iat` and `sub`. Refresh tokens, unknown types and missing types return 401, including on stateless chat. This is the payload claim, not the JWT header `typ: "JWT"`. Existing custom tokens without the claim must be replaced with Go access tokens.

Base URL is the AI service (local `http://localhost:8001`). JSON success and pre-stream errors use `{ "code": 0, "message": "ok", "data": ..., "error": null, "requestId": "..." }`; nonzero `code` represents failure. SSE uses JSON `data:` frames instead of this envelope. `X-Request-ID` is returned in headers. `/docs` and `/openapi.json` exist only when `DOCS_ENABLED=true`.

| Method | Path | Principal | Response |
| --- | --- | --- | --- |
| GET | `/health` | public | process liveness envelope |
| GET | `/ready` | public | database and limiter readiness envelope, 503 if degraded |
| GET | `/metrics` | public if enabled | Prometheus exposition, otherwise 404 |
| GET | `/api/ai/suggestions` | — | `ApiResponse<string[]>` |
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

Create accepts optional `title` (default `New conversation`) and `model` (must match a configured model). Message body requires `content` (1–20,000 characters) and accepts `mode: "auto" | "chat" | "agent"`, `useRag: boolean`. The response is SSE. Detail returns `id`, `userId`, `title`, `model`, `summary`, `createdAt`, `updatedAt`, `messages`. Message objects include `id`, `conversationId`, `sequence`, `role`, `content`, `toolCallId`, `tokenUsage`, `latencyMs`, `citations`, `createdAt`. List omits `messages`. See [Conversations](/conversations).

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
| 5000 | 500 | internal error |
| 5030 | 502 / 503 | provider / coordination unavailable |

Collections accept `page` (1–100000) and `page_size` (1–100, default 50), preserving the existing list envelope. Conversation details return the latest 100 messages by default; use `page_size` and `before=<sequence>` for earlier pages. Message responses expose `sequence`. Context loads at most 200 recent messages, bounds summarization input, and preserves the newest user turn or rejects it if too large. Persistent message content is limited to 20000 characters and the configured context budget. Old `/api/*` paths remain; every business route also has an `/api/v1/*` alias.

## Starter prompts

`GET /api/ai/suggestions` returns three curated strings in `data` inside the standard JSON envelope. It is public, does not call a model and does not save history. `/api/v1/ai/suggestions` is equivalent.

`locale` accepts `en-US` (default), `zh-CN`, or `ja-JP`. Other values return HTTP 422 / code 4001. `Accept-Language` is not used.

```bash
curl -s 'http://localhost:8001/api/ai/suggestions?locale=zh-CN'
```
