# 配置参考

所有配置都从环境变量读取（可选地从 `.env` 文件预置）。设置是**主动校验**的：不安全的组合会在启动时失败，
而不是等到第一个请求才报错。

## 完整参考

| 变量 | 默认值 | 说明 |
|---|---|---|
| `APP_ENV` | `development` | `development` \| `test` \| `production`。 |
| `DEBUG` | `false` | FastAPI 调试模式。 |
| `DOCS_ENABLED` | `true` | 是否提供 `/docs`、`/redoc`、`/openapi.json`。 |
| `LOG_LEVEL` | `INFO` | `DEBUG` \| `INFO` \| `WARNING` \| `ERROR`。 |
| `LOG_FORMAT` | `text` | `text` 用于本地开发，生产环境必须为 `json`。 |
| `CORS_ORIGINS` | `http://localhost:5173,…` | 逗号分隔的浏览器源白名单。 |
| `TRUSTED_HOSTS` | `localhost,127.0.0.1,testserver` | 允许的 `Host` 头值。 |
| `SERVICE_TOKEN` | — | 网关到服务调用的共享密钥。生产环境必填。 |
| `AI_AUTH_REQUIRED` | `false` | 为 `true` 时拒绝匿名访问。 |
| `JWT_SECRET` | dev 占位符 | **必须**与业务服务一致。 |
| `JWT_ISSUER` | `vue-h5-template` | 必须与业务服务一致。 |
| `JWT_AUDIENCE` | `vue-h5-template-api` | 必须与业务服务一致。 |
| `AI_PROVIDER` | `mock` | `mock` \| `openai-compatible`。 |
| `AI_BASE_URL` | `https://api.openai.com/v1` | 任意 OpenAI 兼容端点。 |
| `AI_API_KEY` | — | `openai-compatible` 时必填。 |
| `AI_MODEL` | `gpt-4o-mini` | 发给供应商的模型名。 |
| `AI_TIMEOUT_SECONDS` | `60` | 供应商超时（0–300）。 |
| `AI_MAX_OUTPUT_CHARS` | `20000` | 单轮对话的字符硬上限。 |
| `AI_RATE_LIMIT_PER_MINUTE` | `20` | 每身份、每分钟。 |
| `REDIS_URL` | — | 为空使用进程内限流；多实例运行时需设置。 |

## 生产环境校验

当 `APP_ENV=production` 时，除非满足以下条件，否则启动会拒绝运行：

- `DEBUG` 为 `false` 且 `DOCS_ENABLED` 为 `false`。
- `LOG_FORMAT` 为 `json`。
- 已设置 `SERVICE_TOKEN`。
- `JWT_SECRET` 不是默认占位符。
- `AI_PROVIDER=openai-compatible` 时已设置 `AI_API_KEY`。
- `CORS_ORIGINS` 不包含 `*`。

另外，在 `JWT_SECRET` 仍是占位符时启用 `AI_AUTH_REQUIRED` 也会被拒绝 —— 否则任何人都能签发本服务接受的令牌。

## 认证模型

按优先级识别三种调用方：

1. **service** —— 携带 `SERVICE_TOKEN` 的受信网关。
2. **user** —— 业务服务签发的 JWT（`HS256`，强制校验 issuer/audience/expiry）。
3. **anonymous** —— 仅在 `AI_AUTH_REQUIRED` 为 `false` 时允许。
