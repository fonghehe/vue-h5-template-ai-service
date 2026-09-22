# 配置参考

`app/core/config.py` 的 `Settings` 读取环境变量和可选 `.env`。仓库**只提供** `.env.example`，没有 `.env.development` 或 `.env.production`；未知变量会忽略。

| 分组 | 实际变量与默认值 |
|---|---|
| 服务 | `APP_ENV=development`、`DEBUG=false`、`DOCS_ENABLED=true`、`LOG_LEVEL=INFO`、`LOG_FORMAT=text` |
| HTTP | `CORS_ORIGINS` 默认 localhost:5173；`TRUSTED_HOSTS` 默认 localhost、127.0.0.1、testserver |
| 数据 | `DATABASE_URL=sqlite+aiosqlite:///./.data/ai-service.db`、`DATABASE_AUTO_CREATE=true` |
| 安全 | `SERVICE_TOKEN` 未设、`AI_AUTH_REQUIRED=false`、`JWT_SECRET` 开发占位值、`JWT_ISSUER=vue-h5-template`、`JWT_AUDIENCE=vue-h5-template-api` |
| Provider | `AI_PROVIDER=mock`、`AI_BASE_URL=https://api.openai.com/v1`、`AI_API_KEY` 未设、`AI_MODEL=gpt-4o-mini`、`AI_TIMEOUT_SECONDS=60` |
| 输入/重试 | `AI_MAX_OUTPUT_CHARS=20000`、`AI_MAX_INPUT_CHARS=100000`、`AI_CONTEXT_TOKEN_BUDGET=8000`、`AI_SUMMARY_TOKEN_BUDGET=1000`、`AI_PROVIDER_MAX_RETRIES=3`、`AI_RETRY_BASE_SECONDS=0.25` |
| 路由 | `MODEL_SIMPLE_CHAT`、`MODEL_REASONING`、`MODEL_SUMMARIZATION` 未设时回退到 `AI_MODEL`；`MODEL_EMBEDDING=text-embedding-3-small`、`EMBEDDING_DIMENSIONS=1536` |
| Agent/Go | `AGENT_MAX_ITERATIONS=5`、`BUSINESS_SERVICE_URL=http://localhost:8002`、`BUSINESS_SERVICE_TOKEN` 未设、`BUSINESS_SERVICE_TIMEOUT_SECONDS=5` |
| 知识 | `KNOWLEDGE_MAX_FILE_BYTES=5000000`、`KNOWLEDGE_CHUNK_CHARS=1200`、`KNOWLEDGE_CHUNK_OVERLAP_CHARS=200`、`KNOWLEDGE_TOP_K=5` |
| 配额 | `AI_RATE_LIMIT_PER_MINUTE=20`、`AI_CONCURRENT_STREAM_LIMIT=3`、`AI_DAILY_TOKEN_LIMIT=200000`、`REDIS_URL` 未设 |
| 观测 | `METRICS_ENABLED=true`、`OTEL_ENABLED=false`、`OTEL_SERVICE_NAME=vue-h5-template-ai-service` |

`APP_ENV` 支持 local、development、test、staging、production。staging/production 强制认证、Redis、明确的 Trusted Hosts、至少 32 字节的非占位 JWT 和服务密钥、关闭 DEBUG/docs、JSON 日志、异步 PostgreSQL、使用迁移而非自动建表，以及无通配 CORS。远程模型需要凭据与 HTTPS。更换 Embedding 需要主动重建向量，不会自动迁移维度。


| Pool / HTTP | `DATABASE_POOL_SIZE=5`, `DATABASE_MAX_OVERFLOW=10`, `DATABASE_POOL_TIMEOUT=10`, `DATABASE_POOL_RECYCLE=1800`, `REDIS_MAX_CONNECTIONS=50`, `MAX_REQUEST_BYTES=6000000`, `READINESS_TIMEOUT_SECONDS=3` |
| SSE | `AI_STREAM_TIMEOUT_SECONDS=90`, `SSE_HEARTBEAT_SECONDS=15` |
