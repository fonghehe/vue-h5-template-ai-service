# SSE 协议

两个聊天端点均返回 `text/event-stream`，每帧是一行 `data:` 后跟紧凑 JSON，不使用命名 `event:`。`POST /api/ai/chat` 保留 `@vh5/ai-chat` 的四种原有类型。

| 类型 | 字段 | 端点 |
|---|---|---|
| `start` | `id` | 两者 |
| `delta` | `delta` 文本 | 两者 |
| `finish` | `reason` | 两者 |
| `error` | `message`, optional `code`, `requestId` | 两者 |
| `thinking_status` | 可展示给用户的 `status` | 持久化端点 |
| `tool_start`、`tool_result` | `tool`、`callId`、可选 `result` | Agent |
| `sources` | 引用数组 | RAG |

```text
data: {"type":"start","id":"conversation-id"}

data: {"type":"delta","delta":"你好"}

data: {"type":"finish","reason":"stop"}

```

正常完成会发 `finish: stop`。schema 允许 `abort` 和 `error` reason，但当前路由失败时发送 `error` 事件；断连客户端通常收不到终止帧。新增事件只在持久化端点出现，不影响旧端点。

客户端用 `fetch` 发送 JSON POST 和 Authorization，关闭页面时取消请求。`guarded_stream` 检测断连，取消并等待唯一的待处理读取任务，并关闭直接流、Agent 和 Provider 迭代器。空闲时默认每 15 秒发送 `: heartbeat` SSE 注释，不新增 JSON 事件类型。整个流默认截止时间为 90 秒，包含上下文、工具、持久化和背压；发送另有 5 秒关闭余量。Agent 只做有界工具规划，最终答案直接逐片段输出。为持久化保留的正文受输出上限约束，每个片段先即时发送。

流开始前的校验、认证、配额错误返回 HTTP 状态和 JSON 信封；开始后只能发 SSE `error`。响应包含 `Cache-Control: no-cache, no-transform`、`X-Accel-Buffering: no`，代理需对两个聊天端点关闭缓冲。参见[部署](/zh/deployment)。
