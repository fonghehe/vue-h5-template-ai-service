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

JWT 验证 HS256、`exp`、`iat`、`sub`、issuer、audience；用户资源始终需要用户 JWT。生产 `APP_ENV=production` 要求关闭 DEBUG/docs、JSON 日志、非空 `SERVICE_TOKEN`、非占位 JWT Secret、PostgreSQL async URL、关闭自动建表、无通配 CORS；OpenAI-compatible 还需 API Key。**生产校验并不强制 `AI_AUTH_REQUIRED=true`**，对外暴露前必须自行设定。更换 Embedding 模型/维度不会自动重建旧向量。参见[部署](/zh/deployment)。
