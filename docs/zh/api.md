# API 参考

AI 服务暴露三个端点。非流式响应（以及流开始前的错误）使用与 Go 业务服务相同的信封。

## 响应信封

```jsonc
{ "code": 0,     "message": "ok", "data": { "…": "…" }, "error": null, "requestId": "…" }
{ "code": 4010,  "message": "Authentication required", "data": null, "error": null, "requestId": "…" }
```

`code === 0` 表示成功 —— 与 `@vh5/api-client` 采用相同的分支。

## 端点

| 方法 | 路径 | 鉴权 | 说明 |
|---|---|---|---|
| `GET` | `/health` | — | 存活探针；不触碰任何依赖。 |
| `GET` | `/ready` | — | 就绪探针；报告限流器健康度。 |
| `POST` | `/api/ai/chat` | 可选 | 以 Server-Sent Events 流式返回补全结果。 |

### POST /api/ai/chat

**Body**

```jsonc
{
  "messages": [
    { "role": "user", "content": "为什么流式很有用？", "id": "…", "createdAt": 1700000000 }
  ],
  "conversationId": "conversation-9f2c…" // 可选
}
```

- `role` 为 `system` | `user` | `assistant`。
- `messages` 要求 1–100 条；每条 `content` 上限 20000 字符。
- `id` 与 `createdAt` 可选。

**响应** —— 按 [SSE 契约](/zh/sse) 返回的 `text/event-stream`。

### GET /health

```jsonc
{
  "code": 0,
  "message": "ok",
  "data": {
    "service": "ai",
    "status": "ok",
    "env": "development",
    "version": "1.0.0",
    "provider": "mock",
    "rateLimiter": "memory"
  },
  "error": null,
  "requestId": "…"
}
```

### GET /ready

结构同 `/health`，限流器健康时 `status` 为 `ready`，否则为 `degraded`（HTTP 503）。服务对 chat 是**失败开放**
的，但编排系统应将降级的限流器视为不健康。

## 错误码

| 码 | 含义 | HTTP |
|---|---|---|
| `0` | 成功 | 200 |
| `4000` | 请求错误 | 400 |
| `4001` | 校验失败 | 422 |
| `4010` | 未授权 | 401 |
| `4030` | 禁止访问 | 403 |
| `4040` | 未找到 | 404 |
| `4090` | 冲突 | 409 |
| `4290` | 被限流 | 429 |
| `5000` | 内部错误 | 500 |
| `5030` | 供应商不可用 | 502 |

校验错误只暴露字段**名称** —— 绝不暴露提交的值，因为其中可能包含凭据或个人信息。

## 限流

每个调用方按身份作为配额键：

- 已认证调用方 —— 按 JWT subject；
- 匿名调用方 —— 按客户端 IP（这样共享 NAT 时一个用户无法耗尽他人的配额）。

限制为每分钟 `AI_RATE_LIMIT_PER_MINUTE`。未设置 `REDIS_URL` 时计数器在进程内；多副本运行时需设置
`REDIS_URL`。
