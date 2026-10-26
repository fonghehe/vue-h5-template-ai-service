# API 参考

用户 JWT 必须由 Go 签发，除有效 HS256 签名、issuer、audience、`exp`、`iat` 和 `sub` 外，还必须含载荷声明 `typ: "access"`。刷新令牌、未知类型及缺失类型均返回 401，无状态聊天也适用。这里检查的是载荷声明，不是 JWT 头部的 `typ: "JWT"`。已有缺失该声明的自定义令牌需要换成 Go access token。

本地 Base URL 为 `http://localhost:8001`。普通 JSON 成功和流开始前错误使用 `{ "code":0, "message":"ok", "data":..., "error":null, "requestId":"..." }`；非零 code 为错误。SSE 不用该信封。响应头含 `X-Request-ID`。`/docs`、`/openapi.json` 仅在 `DOCS_ENABLED=true` 时开放。

| 方法 | 路径 | 身份 | 响应 |
| --- | --- | --- | --- |
| GET | `/health` | 公开 | 进程存活 |
| GET | `/ready` | 公开 | 数据库与限流器就绪；降级为 503 |
| GET | `/metrics` | 开启时公开 | Prometheus，关闭则 404 |
| GET | `/api/ai/suggestions` | — | `ApiResponse<string[]>` |
| POST | `/api/ai/chat` | 允许时用户/服务/匿名 | 旧 SSE，不持久化 |
| POST、GET | `/api/conversations` | 用户 JWT | 创建/列表 |
| GET、DELETE | `/api/conversations/{id}` | 所有者 JWT | 详情/删除 |
| POST | `/api/conversations/{id}/messages` | 所有者 JWT | 持久化 SSE |
| POST、GET | `/api/knowledge/documents` | 用户 JWT | 上传/列表 |
| DELETE | `/api/knowledge/documents/{id}` | 所有者 JWT | 删除 |
| GET | `/api/usage/me` | 用户 JWT | 汇总与分组 |

## 旧聊天端点

```bash
curl -N http://localhost:8001/api/ai/chat -H 'Content-Type: application/json' -d '{"messages":[{"role":"user","content":"你好"}]}'
```

Body 要求 `messages`（1–100 条），可选 `conversationId`（最多 120 字符）。每条消息有 `role`（`system`、`user`、`assistant`、`tool`）、`content`（最多 20000 字符），以及可选 `id`、`createdAt`、`toolCalls`、`toolCallId`。`tool` 消息必须有 `toolCallId`；空内容必须有 tool call。总内容最多 100000 字符。该端点使用客户端提供的历史，不保存。详见 [SSE](/zh/sse)。

## 会话

```bash
curl -s http://localhost:8001/api/conversations -H "Authorization: Bearer $AI_USER_JWT" -H 'Content-Type: application/json' -d '{"title":"购物咨询"}'
curl -N "http://localhost:8001/api/conversations/$AI_CONVERSATION_ID/messages" -H "Authorization: Bearer $AI_USER_JWT" -H 'Content-Type: application/json' -d '{"content":"找 500 元以下的商品","mode":"agent","useRag":false}'
```

创建可提供 `title`（默认 `New conversation`）和 `model`（必须是已配置模型）。消息请求要求 `content`（1–20000 字符），可选 `mode: "auto" | "chat" | "agent"`、`useRag: boolean`，响应为 SSE。详情返回 `id`、`userId`、`title`、`model`、`summary`、`createdAt`、`updatedAt`、`messages`；消息含 `id`、`conversationId`、`sequence`、`role`、`content`、`toolCallId`、`tokenUsage`、`latencyMs`、`citations`、`createdAt`。列表不返回消息。参见[会话](/zh/conversations)。

## 知识库与用量

```bash
curl -s http://localhost:8001/api/knowledge/documents -H "Authorization: Bearer $AI_USER_JWT" -F 'file=@notes.md' -F 'metadata={"topic":"catalog"}'
curl -s http://localhost:8001/api/usage/me -H "Authorization: Bearer $AI_USER_JWT"
```

上传支持 txt、md、pdf；`metadata` 是表单中的 JSON 对象字符串，默认 `{}`。文档响应含 `id`、`title`、`source`、`metadata`、`createdAt`，列表/删除限定所有者。用量返回 `promptTokens`、`completionTokens`、`totalTokens`、`requests` 及 `byModel`、`byConversation`、`byDate`。旧聊天不计入。

## 错误与限制

| code               | HTTP            | 含义                       |
| ------------------ | --------------- | -------------------------- |
| 4000 / 4001        | 400 / 422       | 错误请求 / Pydantic 校验   |
| 4010 / 4030 / 4040 | 401 / 403 / 404 | 认证 / 所有权 / 不存在     |
| 4090 / 4290        | 409 / 429       | 冲突 / 配额                |
| 5000 | 500 | 内部错误 |
| 5030 | 502 / 503 | Provider／协调后端不可用 |

列表支持 `page`（1–100000）、`page_size`（1–100，默认 50），保留原列表信封。会话详情默认返回最近 100 条消息，通过 `page_size` 和 `before=<sequence>` 查询更早消息；消息新增 `sequence`。上下文最多读取最近 200 条，摘要输入有上限，保留最新用户消息，过大时拒绝。持久化消息同时受 20000 字符和上下文预算限制。旧 `/api/*` 路径保留，业务路由新增 `/api/v1/*` 别名。

## 聊天建议

`GET /api/ai/suggestions` 在标准 JSON 信封的 `data` 中返回三条固定建议。接口公开，不调用模型，不保存历史；`/api/v1/ai/suggestions` 等价。

`locale` 支持 `en-US`（默认）、`zh-CN`、`ja-JP`；其他值返回 HTTP 422／业务码 4001。不使用 `Accept-Language`。

```bash
curl -s 'http://localhost:8001/api/ai/suggestions?locale=zh-CN'
```
