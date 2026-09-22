# SSE protocol

Both chat routes return `text/event-stream` with compact JSON on a `data:` line, without a named `event:` field. The legacy `POST /api/ai/chat` keeps the four `@vh5/ai-chat` types.

| Type | Fields | Route |
|---|---|---|
| `start` | `id` | both |
| `delta` | `delta` text | both |
| `finish` | `reason` | both |
| `error` | `message`, optional `code`, `requestId` | both |
| `thinking_status` | user-visible `status` | persistent |
| `tool_start`, `tool_result` | `tool`, `callId`, optional `result` | persistent agent |
| `sources` | citations | persistent RAG |

```text
data: {"type":"start","id":"conversation-id"}

data: {"type":"delta","delta":"Hello"}

data: {"type":"finish","reason":"stop"}

```

Successful routes emit `finish` with `stop`. The schema allows `abort` and `error` reasons, but the implemented routes use an `error` event on failure. A disconnected client normally sees no terminal frame. Optional events are additive and never sent by the legacy endpoint.

Use `fetch` with JSON POST and Authorization and abort when the view closes. `guarded_stream` polls disconnection, cancels and joins its single pending read, and closes direct/agent/provider generators on cancellation or timeout. Idle responses emit `: heartbeat` SSE comments (15 seconds by default), not extra JSON event types. The whole stream has a 90-second deadline, including context, tools, persistence and backpressure; sending has a further 5-second shutdown allowance. Agent planning is bounded; final generation uses provider deltas immediately. Completed conversation text is retained up to the output cap for persistence, never accumulated before sending.

Pre-stream validation/auth/quota failures return an HTTP status and JSON envelope. Errors after headers become SSE `error`. Response headers include `Cache-Control: no-cache, no-transform` and `X-Accel-Buffering: no`; disable proxy buffering for both chat routes. See [Deployment](/deployment).
