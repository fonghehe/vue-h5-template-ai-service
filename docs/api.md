# API reference

The AI service exposes three endpoints. Non-streaming responses (and pre-stream errors) use the same envelope as
the Go business service.

## Response envelope

```jsonc
{ "code": 0,     "message": "ok", "data": { "…": "…" }, "error": null, "requestId": "…" }
{ "code": 4010,  "message": "Authentication required", "data": null, "error": null, "requestId": "…" }
```

`code === 0` means success — the same branch `@vh5/api-client` takes.

## Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/health` | — | Liveness probe; never touches dependencies. |
| `GET` | `/ready` | — | Readiness probe; reports limiter health. |
| `POST` | `/api/ai/chat` | optional | Stream a chat completion as Server-Sent Events. |

### POST /api/ai/chat

**Body**

```jsonc
{
  "messages": [
    { "role": "user", "content": "Why is streaming useful?", "id": "…", "createdAt": 1700000000 }
  ],
  "conversationId": "conversation-9f2c…" // optional
}
```

- `role` is `system` | `user` | `assistant`.
- `messages` requires 1–100 entries; each `content` is capped at 20 000 characters.
- `id` and `createdAt` are accepted but not required.

**Response** — a `text/event-stream` per [the SSE contract](/sse).

### GET /health

```jsonc
{
  "code": 0,
  "message": "ok",
  "data": {
    "service": "ai",
    "status": "ok",
    "env": "development",
    "version": "1.0.0",
    "provider": "mock",
    "rateLimiter": "memory"
  },
  "error": null,
  "requestId": "…"
}
```

### GET /ready

Same shape as `/health`, with `status` set to `ready` when the rate limiter is healthy and `degraded` (HTTP 503)
otherwise. The service fails open for chat, but orchestrators should treat a degraded limiter as unhealthy.

## Error codes

| Code | Meaning | HTTP |
|---|---|---|
| `0` | Success | 200 |
| `4000` | Bad request | 400 |
| `4001` | Validation failed | 422 |
| `4010` | Unauthorized | 401 |
| `4030` | Forbidden | 403 |
| `4040` | Not found | 404 |
| `4090` | Conflict | 409 |
| `4290` | Rate limited | 429 |
| `5000` | Internal error | 500 |
| `5030` | Provider unavailable | 502 |

Validation errors surface only field **names** — never the submitted values, which may contain credentials or
personal data.

## Rate limiting

Each caller is quota-keyed by identity:

- authenticated callers — by JWT subject;
- anonymous callers — by client IP (so a shared NAT cannot let one user exhaust another's quota).

The limit is `AI_RATE_LIMIT_PER_MINUTE` per minute. With no `REDIS_URL`, the counter is in-process; set `REDIS_URL`
when running more than one replica.
