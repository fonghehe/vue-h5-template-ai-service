# 配置参考

`app/core/config.py` 是默认值和校验规则的依据。进程环境变量优先于 `.env`，未知变量会忽略。本地开发可复制 `.env.example`，不要将真实凭据提交到仓库。下表时间单位为秒；大小按变量名分别表示字节或字符。

## 接入 HTTP 模型

在后端环境设置 Provider 地址、密钥和模型，不要将凭据放入前端 `VITE_*`。任务专用 `MODEL_*` 未设时回退到 `AI_MODEL`；Embedding 使用独立模型。超时和重试含义见 [SSE](./sse.md)。

```dotenv
AI_PROVIDER=openai-compatible
AI_BASE_URL=https://api.openai.com/v1
AI_API_KEY=<provider-key>
AI_MODEL=<model-id>
```

## Provider 与流式输出

| 变量 | 默认值 |
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
| `MODEL_SIMPLE_CHAT` | 未设置 |
| `MODEL_REASONING` | 未设置 |
| `MODEL_SUMMARIZATION` | 未设置 |
| `MODEL_EMBEDDING` | `text-embedding-3-small` |
| `EMBEDDING_DIMENSIONS` | `1536` |
| `AI_API_KEY` | 未设置 |

## 认证与配额

| 变量 | 默认值 |
|---|---|
| `AI_AUTH_REQUIRED` | `false` |
| `JWT_SECRET` | `dev-only-change-me-before-production` |
| `JWT_ISSUER` | `vue-h5-template` |
| `JWT_AUDIENCE` | `vue-h5-template-api` |
| `SERVICE_TOKEN` | 未设置 |
| `AI_RATE_LIMIT_PER_MINUTE` | `20` |
| `AI_CONCURRENT_STREAM_LIMIT` | `3` |
| `AI_DAILY_TOKEN_LIMIT` | `200000` |

## 数据库与 Redis

| 变量 | 默认值 |
|---|---|
| `DATABASE_URL` | `sqlite+aiosqlite:///./.data/ai-service.db` |
| `DATABASE_AUTO_CREATE` | `true` |
| `DATABASE_POOL_SIZE` | `5` |
| `DATABASE_MAX_OVERFLOW` | `10` |
| `DATABASE_POOL_TIMEOUT` | `10` |
| `DATABASE_POOL_RECYCLE` | `1800` |
| `REDIS_URL` | 未设置 |
| `REDIS_MAX_CONNECTIONS` | `50` |

## 工具与知识库

| 变量 | 默认值 |
|---|---|
| `AGENT_MAX_ITERATIONS` | `5` |
| `BUSINESS_SERVICE_URL` | `http://localhost:8002` |
| `BUSINESS_SERVICE_TOKEN` | 未设置 |
| `BUSINESS_SERVICE_TIMEOUT_SECONDS` | `5` |
| `KNOWLEDGE_MAX_FILE_BYTES` | `5000000` |
| `KNOWLEDGE_CHUNK_CHARS` | `1200` |
| `KNOWLEDGE_CHUNK_OVERLAP_CHARS` | `200` |
| `KNOWLEDGE_TOP_K` | `5` |

## 服务与 HTTP

| 变量 | 默认值 |
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

## JWT 与生产要求

用户 JWT 必须是 Go 签发的 access token：HS256 签名、有效 issuer/audience、`exp`、`iat`、`sub`，以及载荷中的 `typ="access"`。刷新令牌或缺少类型会返回 401。`SERVICE_TOKEN` 可用于内部服务访问无状态聊天，不能访问用户私有资源。

`APP_ENV` 支持 `local`、`development`、`test`、`staging`、`production`。staging/production 启动时强制检查：启用认证、配置 Redis 和异步 PostgreSQL、关闭自动建表/debug/docs、使用 JSON 日志、明确主机白名单、CORS 无通配符。JWT 和服务密钥至少 32 字节，拒绝 JWT 开发占位值。HTTP Provider 必须配置密钥并使用 HTTPS。参见[部署](./deployment.md)。

`AI_DAILY_TOKEN_LIMIT` 只检查成功记录的轮次，不是原子的每日预留或计费账本。更换 Embedding 模型或维度前要制定重新生成向量的方案；现有向量不会自动迁移。
