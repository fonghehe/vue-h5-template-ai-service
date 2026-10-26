# Configuration

`app/core/config.py` is the source of truth for defaults and validation. Process environment variables override `.env`; unknown keys are ignored. Copy `.env.example` for local development and keep credentials outside version control. Durations below are seconds; sizes are bytes or characters as named.

## Connect an HTTP model

Set the provider URL, key and model in the service environment. Never put provider credentials in frontend `VITE_*` variables. Task-specific `MODEL_*` values fall back to `AI_MODEL` when unset; embedding uses its own model. See [SSE](./sse.md) for timeout and retry behavior.

```dotenv
AI_PROVIDER=openai-compatible
AI_BASE_URL=https://api.openai.com/v1
AI_API_KEY=<provider-key>
AI_MODEL=<model-id>
```

## Provider and streaming

| Variable | Default |
|---|---|
| `AI_PROVIDER` | `mock` |
| `AI_BASE_URL` | `https://api.openai.com/v1` |
| `AI_MODEL` | `gpt-4o-mini` |
| `AI_TIMEOUT_SECONDS` | `60` |
| `AI_STREAM_TIMEOUT_SECONDS` | `90` |
| `SSE_HEARTBEAT_SECONDS` | `15` |
| `AI_MAX_INPUT_CHARS` | `100000` |
| `AI_MAX_OUTPUT_CHARS` | `20000` |
| `AI_CONTEXT_TOKEN_BUDGET` | `8000` |
| `AI_SUMMARY_TOKEN_BUDGET` | `1000` |
| `AI_PROVIDER_MAX_RETRIES` | `3` |
| `AI_RETRY_BASE_SECONDS` | `0.25` |
| `MODEL_SIMPLE_CHAT` | Unset |
| `MODEL_REASONING` | Unset |
| `MODEL_SUMMARIZATION` | Unset |
| `MODEL_EMBEDDING` | `text-embedding-3-small` |
| `EMBEDDING_DIMENSIONS` | `1536` |
| `AI_API_KEY` | Unset |

## Authentication and quotas

| Variable | Default |
|---|---|
| `AI_AUTH_REQUIRED` | `false` |
| `JWT_SECRET` | `dev-only-change-me-before-production` |
| `JWT_ISSUER` | `vue-h5-template` |
| `JWT_AUDIENCE` | `vue-h5-template-api` |
| `SERVICE_TOKEN` | Unset |
| `AI_RATE_LIMIT_PER_MINUTE` | `20` |
| `AI_CONCURRENT_STREAM_LIMIT` | `3` |
| `AI_DAILY_TOKEN_LIMIT` | `200000` |

## Database and Redis

| Variable | Default |
|---|---|
| `DATABASE_URL` | `sqlite+aiosqlite:///./.data/ai-service.db` |
| `DATABASE_AUTO_CREATE` | `true` |
| `DATABASE_POOL_SIZE` | `5` |
| `DATABASE_MAX_OVERFLOW` | `10` |
| `DATABASE_POOL_TIMEOUT` | `10` |
| `DATABASE_POOL_RECYCLE` | `1800` |
| `REDIS_URL` | Unset |
| `REDIS_MAX_CONNECTIONS` | `50` |

## Tools and knowledge

| Variable | Default |
|---|---|
| `AGENT_MAX_ITERATIONS` | `5` |
| `BUSINESS_SERVICE_URL` | `http://localhost:8002` |
| `BUSINESS_SERVICE_TOKEN` | Unset |
| `BUSINESS_SERVICE_TIMEOUT_SECONDS` | `5` |
| `KNOWLEDGE_MAX_FILE_BYTES` | `5000000` |
| `KNOWLEDGE_CHUNK_CHARS` | `1200` |
| `KNOWLEDGE_CHUNK_OVERLAP_CHARS` | `200` |
| `KNOWLEDGE_TOP_K` | `5` |

## Service and HTTP

| Variable | Default |
|---|---|
| `APP_ENV` | `development` |
| `DEBUG` | `false` |
| `DOCS_ENABLED` | `true` |
| `LOG_LEVEL` | `INFO` |
| `LOG_FORMAT` | `text` |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` |
| `TRUSTED_HOSTS` | `localhost,127.0.0.1,testserver` |
| `MAX_REQUEST_BYTES` | `6000000` |
| `READINESS_TIMEOUT_SECONDS` | `3` |
| `METRICS_ENABLED` | `true` |
| `OTEL_ENABLED` | `false` |
| `OTEL_SERVICE_NAME` | `vue-h5-template-ai-service` |

## JWT and production requirements

User JWTs must be Go-issued access tokens: HS256, valid issuer/audience, `exp`, `iat`, `sub` and payload `typ="access"`. A refresh token or missing type returns 401. `SERVICE_TOKEN` authenticates an internal service for stateless chat; it does not grant access to user-owned resources.

`APP_ENV` accepts `local`, `development`, `test`, `staging`, `production`. Staging/production fail startup unless auth is enabled, Redis and asynchronous PostgreSQL are configured, auto-create/debug/docs are disabled, logs use JSON, hosts are explicit and CORS has no wildcard. JWT and service secrets must be at least 32 bytes; the JWT development placeholder is rejected. HTTP providers require a key and HTTPS. See [Deployment](./deployment.md).

`AI_DAILY_TOKEN_LIMIT` checks completed recorded turns; it is not an atomic daily reservation or billing ledger. Changing embedding models/dimensions requires a deliberate re-embedding plan; existing vectors are not automatically migrated.
