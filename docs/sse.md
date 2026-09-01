# The SSE contract

`POST /api/ai/chat` returns a `text/event-stream` whose events are exactly the `ChatChunk` union consumed by
`@vh5/ai-chat`.

| `type` | Fields | Meaning |
|---|---|---|
| `start` | `id` | Stream accepted; carries the conversation id. |
| `delta` | `delta` | One text fragment; concatenate in order. |
| `finish` | `reason` | Terminal event: `stop`, `abort` or `error`. |
| `error` | `message` | Failure after streaming began; the client throws. |

Each frame is a single `data:` line carrying compact JSON:

```text
data: {"type":"start","id":"conversation-9f2c…"}
data: {"type":"delta","delta":"Streaming "}
data: {"type":"finish","reason":"stop"}
```

## Termination reasons

- `stop` — the provider finished normally.
- `abort` — the client disconnected mid-stream; the service stops promptly instead of paying for unread tokens.
- `error` — reserved for a failure reported through a `FinishChunk` reason in client libraries; the service itself
  emits an `error` event in this case.

## Error handling — before vs. during the stream

- Errors that happen **before** the first byte are returned as a normal JSON error envelope with the proper HTTP
  status and application code.
- Errors that happen **during** the stream become an `error` event, because the HTTP status has already been sent.

## Headers

The response sets headers that stop intermediaries from buffering the stream:

```
Cache-Control: no-cache, no-transform
Connection: keep-alive
X-Accel-Buffering: no
```

If you front the service with nginx, also set `proxy_buffering off;` — see [Deployment](/deployment).
