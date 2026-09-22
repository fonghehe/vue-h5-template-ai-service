# Configuration

`Settings` in `app/core/config.py` reads the process environment and optional `.env`. The repository ships **only** `.env.example`: there are no `.env.development` or `.env.production` files. Unknown keys are ignored.

| Group | Variables and defaults |
|---|---|
| Identity | `APP_ENV=development`, `DEBUG=false`, `DOCS_ENABLED=true`, `LOG_LEVEL=INFO`, `LOG_FORMAT=text` |
| HTTP | `CORS_ORIGINS` (localhost:5173 origins), `TRUSTED_HOSTS` (localhost, 127.0.0.1, testserver) |
| Storage | `DATABASE_URL=sqlite+aiosqlite:///./.data/ai-service.db`, `DATABASE_AUTO_CREATE=true` |
| Security | `SERVICE_TOKEN` unset, `AI_AUTH_REQUIRED=false`, `JWT_SECRET` development placeholder, `JWT_ISSUER=vue-h5-template`, `JWT_AUDIENCE=vue-h5-template-api` |
| Provider | `AI_PROVIDER=mock`, `AI_BASE_URL=https://api.openai.com/v1`, `AI_API_KEY` unset, `AI_MODEL=gpt-4o-mini`, `AI_TIMEOUT_SECONDS=60` |
| Context/retries | `AI_MAX_OUTPUT_CHARS=20000`, `AI_MAX_INPUT_CHARS=100000`, `AI_CONTEXT_TOKEN_BUDGET=8000`, `AI_SUMMARY_TOKEN_BUDGET=1000`, `AI_PROVIDER_MAX_RETRIES=3`, `AI_RETRY_BASE_SECONDS=0.25` |
| Routing | `MODEL_SIMPLE_CHAT`, `MODEL_REASONING`, `MODEL_SUMMARIZATION` unset (fall back to `AI_MODEL`); `MODEL_EMBEDDING=text-embedding-3-small`, `EMBEDDING_DIMENSIONS=1536` |
| Agent/Go | `AGENT_MAX_ITERATIONS=5`, `BUSINESS_SERVICE_URL=http://localhost:8002`, `BUSINESS_SERVICE_TOKEN` unset, `BUSINESS_SERVICE_TIMEOUT_SECONDS=5` |
| Knowledge | `KNOWLEDGE_MAX_FILE_BYTES=5000000`, `KNOWLEDGE_CHUNK_CHARS=1200`, `KNOWLEDGE_CHUNK_OVERLAP_CHARS=200`, `KNOWLEDGE_TOP_K=5` |
| Limits | `AI_RATE_LIMIT_PER_MINUTE=20`, `AI_CONCURRENT_STREAM_LIMIT=3`, `AI_DAILY_TOKEN_LIMIT=200000`, `REDIS_URL` unset |
| Telemetry | `METRICS_ENABLED=true`, `OTEL_ENABLED=false`, `OTEL_SERVICE_NAME=vue-h5-template-ai-service` |

JWT validation enforces HS256, `exp`, `iat`, `sub`, issuer and audience. Persistent resources always require a **user** JWT, even if anonymous legacy chat is allowed. Match the Go issuer settings.

`APP_ENV` accepts local, development, test, staging and production. Staging and production require `AI_AUTH_REQUIRED=true`, Redis, explicit trusted hosts, non-placeholder JWT and service secrets of at least 32 bytes, disabled DEBUG/docs, JSON logs, asynchronous PostgreSQL, migrations instead of auto-create, and no wildcard CORS. Hosted providers require credentials and HTTPS. Embedding changes require deliberate reindexing; dimensions are not automatically migrated.


| Pool / HTTP | `DATABASE_POOL_SIZE=5`, `DATABASE_MAX_OVERFLOW=10`, `DATABASE_POOL_TIMEOUT=10`, `DATABASE_POOL_RECYCLE=1800`, `REDIS_MAX_CONNECTIONS=50`, `MAX_REQUEST_BYTES=6000000`, `READINESS_TIMEOUT_SECONDS=3` |
| SSE | `AI_STREAM_TIMEOUT_SECONDS=90`, `SSE_HEARTBEAT_SECONDS=15` |
