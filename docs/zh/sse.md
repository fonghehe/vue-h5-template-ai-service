# SSE 协议

两个聊天端点均返回 `text/event-stream`，每帧是一行 `data:` 后跟紧凑 JSON，不使用命名 `event:`。`POST /api/ai/chat` 保留 `@vh5/ai-chat` 的四种原有类型。

| 类型 | 字段 | 端点 |
|---|---|---|
| `start` | `id` | 两者 |
| `delta` | `delta` 文本 | 两者 |
| `finish` | `reason` | 两者 |
| `error` | `message` | 两者 |
| `thinking_status` | 可展示给用户的 `status` | 持久化端点 |
| `tool_start`、`tool_result` | `tool`、`callId`、可选 `result` | Agent |
| `sources` | 引用数组 | RAG |

```text
data: {"type":"start","id":"conversation-id"}

data: {"type":"delta","delta":"你好"}

data: {"type":"finish","reason":"stop"}

```

正常完成会发 `finish: stop`。schema 允许 `abort` 和 `error` reason，但当前路由失败时发送 `error` 事件；断连客户端通常收不到终止帧。新增事件只在持久化端点出现，不影响旧端点。

客户端用 `fetch` 发 JSON POST 和 Authorization，原生 `EventSource` 不支持这种请求；页面关闭时取消 fetch。`cancel_aware_stream` 会取消等待中的直接 Provider 读取并关闭迭代器。Agent 可发送工具状态，但先完成图再分块发送答案。

流开始前的校验、认证、配额错误返回 HTTP 状态和 JSON 信封；开始后只能发 SSE `error`。响应包含 `Cache-Control: no-cache, no-transform`、`X-Accel-Buffering: no`，代理需对两个聊天端点关闭缓冲。参见[部署](/zh/deployment)。
