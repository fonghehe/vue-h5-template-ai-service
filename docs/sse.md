# SSE protocol

Use `fetch` to POST JSON and read the response as an SSE stream. Both chat endpoints use `text/event-stream`; each event is JSON after `data:`, separated by a blank line. There is no named `event:` field.

## Events

| Type | Fields | Availability |
|---|---|---|
| `start` | `id` | Both chat endpoints |
| `delta` | `delta` | Both chat endpoints |
| `finish` | `reason` | Both chat endpoints |
| `error` | `message`, `code?`, `requestId?` | Both chat endpoints |
| `thinking_status` | `status` | Persistent conversations only |
| `tool_start` | `tool`, `callId` | Agent mode only |
| `tool_result` | `tool`, `callId`, `result` | Agent mode only |
| `sources` | `sources[]` | RAG only |

```text
data: {"type":"start","id":"conversation-id"}

data: {"type":"delta","delta":"Hello"}

data: {"type":"finish","reason":"stop"}

```

## Completion and errors

A successful stream sends `start`, zero or more `delta` events, then one `finish` with `reason="stop"`. Failure after streaming starts sends `error` instead. Stop reading on either terminal event. The schema also allows finish reasons `abort` and `error`, but current routes do not emit them.

Before streaming, authentication, validation and admission failures return an HTTP error and the standard JSON envelope. A disconnected client may receive no terminal event. Do not automatically replay a POST after receiving a delta: a new request can duplicate a turn or a tool operation.

## Timeouts, heartbeat and retries

| Control | Default | Meaning |
|---|---|---|
| `AI_TIMEOUT_SECONDS` | 60 s | For the HTTP provider: transport timeout and, per stream attempt, first-content-token / token-idle wait. Comments and empty deltas do not renew the token budget. |
| `AI_STREAM_TIMEOUT_SECONDS` | 90 s | Turn deadline covering context, tools, persistence and client backpressure. HTTP delivery has an additional 5-second termination allowance. |
| `SSE_HEARTBEAT_SECONDS` | 15 s | While waiting for work, send `: heartbeat` comments. These are not JSON events or model tokens. |

The OpenAI-compatible adapter accepts `[DONE]` or a nonempty `finish_reason` as upstream termination. EOF without either becomes an error. Usage-only chunks are accepted. Transient provider failures may retry before the first content delta, subject to `AI_PROVIDER_MAX_RETRIES`; malformed or truncated streams are not retried.

## Cancellation and resource ownership

Abort the fetch when the view closes. The service keeps at most one pending upstream read; disconnect, timeout or failed delivery cancels that read, waits for it to exit, and closes the guarded, provider and nested graph iterators. Cleanup attempts remaining resources even if a close fails. Shared HTTP clients belong to application lifespan, not individual turns.

Conversation text is sent incrementally and retained only up to the output cap for persistence. The completed assistant reply, tool history and usage commit together before `finish`. An interrupted turn can leave a saved user message without an assistant reply.

## Proxy settings

Responses include `Cache-Control: no-cache, no-transform` and `X-Accel-Buffering: no`. Disable proxy buffering for both chat endpoints and their `/api/v1` aliases. See [Deployment](./deployment.md).
