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

For `APP_ENV=production`, validation requires `DEBUG=false`, `DOCS_ENABLED=false`, `LOG_FORMAT=json`, nonempty `SERVICE_TOKEN`, non-placeholder `JWT_SECRET`, a PostgreSQL async URL, `DATABASE_AUTO_CREATE=false` and no wildcard CORS. OpenAI-compatible mode also needs `AI_API_KEY`. **Production validation does not require `AI_AUTH_REQUIRED=true`**; explicitly set it before exposure. Changing embedding model/dimensions requires compatible stored vectors and migration planning; it does not reindex automatically. See [Deployment](/deployment).
