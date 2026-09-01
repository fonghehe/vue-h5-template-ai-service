# Architecture

The service is an application-factory FastAPI app with process-wide dependencies created and disposed in the
lifespan hook.

```
app/main.py            app factory, lifespan, middleware, exception handlers
app/core/config.py     fail-fast settings
app/core/security.py   principal resolution (service / user / anonymous)
app/core/errors.py     error codes (aligned with the business service)
app/core/logging.py    JSON / text logging with request scope
app/providers/         ChatProvider abstraction + factory (mock / openai-compatible)
app/schemas/           request + SSE chunk + envelope models
app/services/          rate limiter (memory / redis)
app/api/v1/            routes (chat, system)
```

## Request lifecycle

1. **Trusted host + CORS + request-context middleware** assign a correlation id and emit one access-log line per
   request.
2. **Authentication** resolves the principal: service token → user JWT → anonymous.
3. **The handler** validates input, enforces the rate limit, then streams provider fragments as SSE frames.
4. **Exception handlers** map `AppError` and `RequestValidationError` onto the shared JSON envelope.

## Provider abstraction

Model access sits behind `ChatProvider`:

- `MockChatProvider` — a canned stream, so the whole transport works offline in development and tests.
- `OpenAICompatibleProvider` — any OpenAI-compatible endpoint via `httpx`.

The factory (`app/providers/factory.py`) selects one at startup from `AI_PROVIDER`; swapping providers changes
nothing in the transport or the frontend.

## Streaming behaviour

- The stream emits `start`, zero or more `delta`, then `finish`.
- The handler polls `request.is_disconnected()` between fragments and aborts early when the browser navigates away,
  avoiding paid-for tokens nobody reads.
- A failure mid-stream is reported as an `error` event with a client-safe message — provider internals never leak.

## Cross-service identity

`JWT_SECRET`, `JWT_ISSUER` and `JWT_AUDIENCE` must match the business service, so a user who logged in there is
already authenticated here. A `SERVICE_TOKEN` additionally lets a trusted gateway call on behalf of its own users.
