# Configuration

All configuration is read from the environment (optionally seeded from a `.env` file). Settings are validated
eagerly: an unsafe combination fails at startup rather than at the first request.

## Full reference

| Variable | Default | Description |
|---|---|---|
| `APP_ENV` | `development` | `development` \| `test` \| `production`. |
| `DEBUG` | `false` | FastAPI debug mode. |
| `DOCS_ENABLED` | `true` | Serve `/docs`, `/redoc`, `/openapi.json`. |
| `LOG_LEVEL` | `INFO` | `DEBUG` \| `INFO` \| `WARNING` \| `ERROR`. |
| `LOG_FORMAT` | `text` | `text` for local dev, `json` (required in production). |
| `CORS_ORIGINS` | `http://localhost:5173,…` | Comma-separated browser origin allow-list. |
| `TRUSTED_HOSTS` | `localhost,127.0.0.1,testserver` | Allowed `Host` header values. |
| `SERVICE_TOKEN` | — | Shared secret for gateway-to-service calls. Required in production. |
| `AI_AUTH_REQUIRED` | `false` | When `true`, anonymous access is refused. |
| `JWT_SECRET` | dev placeholder | **Must** match the business service. |
| `JWT_ISSUER` | `vue-h5-template` | Must match the business service. |
| `JWT_AUDIENCE` | `vue-h5-template-api` | Must match the business service. |
| `AI_PROVIDER` | `mock` | `mock` \| `openai-compatible`. |
| `AI_BASE_URL` | `https://api.openai.com/v1` | Any OpenAI-compatible endpoint. |
| `AI_API_KEY` | — | Required for `openai-compatible`. |
| `AI_MODEL` | `gpt-4o-mini` | Model sent to the provider. |
| `AI_TIMEOUT_SECONDS` | `60` | Provider timeout (0–300). |
| `AI_MAX_OUTPUT_CHARS` | `20000` | Hard ceiling on a single turn, in characters. |
| `AI_RATE_LIMIT_PER_MINUTE` | `20` | Per identity, per minute. |
| `REDIS_URL` | — | Empty = in-process limiter; set for multi-instance runs. |

## Production validation

When `APP_ENV=production`, startup refuses to run unless:

- `DEBUG` is `false` and `DOCS_ENABLED` is `false`.
- `LOG_FORMAT` is `json`.
- `SERVICE_TOKEN` is set.
- `JWT_SECRET` is not the default placeholder.
- `AI_API_KEY` is set when `AI_PROVIDER=openai-compatible`.
- `CORS_ORIGINS` does not contain `*`.

Additionally, enabling `AI_AUTH_REQUIRED` while `JWT_SECRET` is still the placeholder is rejected — otherwise anyone
could mint a token the service accepts.

## Authentication model

Three caller kinds are recognised, in precedence order:

1. **service** — a trusted gateway presenting `SERVICE_TOKEN`.
2. **user** — a JWT minted by the business service (`HS256`, issuer/audience/expiry enforced).
3. **anonymous** — allowed only while `AI_AUTH_REQUIRED` is `false`.
