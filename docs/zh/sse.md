# SSE 协议

客户端使用 `fetch` 发送 JSON POST，并按 SSE 读取响应。两个聊天端点均返回 `text/event-stream`：每个事件由 `data:` 后的 JSON 和一个空行组成，不使用命名 `event:` 字段。

## 事件类型

| 类型 | 字段 | 使用范围 |
|---|---|---|
| `start` | `id` | 两个聊天端点 |
| `delta` | `delta` | 两个聊天端点 |
| `finish` | `reason` | 两个聊天端点 |
| `error` | `message`, `code?`, `requestId?` | 两个聊天端点 |
| `thinking_status` | `status` | 仅持久化会话 |
| `tool_start` | `tool`, `callId` | 仅 Agent 模式 |
| `tool_result` | `tool`, `callId`, `result` | 仅 Agent 模式 |
| `sources` | `sources[]` | 仅 RAG |

```text
data: {"type":"start","id":"conversation-id"}

data: {"type":"delta","delta":"Hello"}

data: {"type":"finish","reason":"stop"}

```

## 完成与错误

成功时依次发送 `start`、零个或多个 `delta`，最后发送一个 `finish`，其中 `reason="stop"`。流开始后失败则发送 `error`。客户端收到任一终止事件后应结束读取。schema 还允许 `abort`、`error` 两种 finish reason，但当前路由不发送它们。

流开始前的认证、校验或准入失败返回 HTTP 错误和标准 JSON 信封。客户端断连时可能收不到终止事件。收到 delta 后不要自动重放 POST，否则可能重复创建轮次或执行工具操作。

## 超时、心跳与重试

| 配置 | 默认值 | 作用 |
|---|---|---|
| `AI_TIMEOUT_SECONDS` | 60 秒 | HTTP Provider 的传输超时；每次流尝试中也限制首个内容 token 和后续 token 的等待。注释、空 delta 不刷新 token 等待预算。 |
| `AI_STREAM_TIMEOUT_SECONDS` | 90 秒 | 覆盖上下文、工具、持久化和客户端背压的轮次截止时间；HTTP 发送另有 5 秒终止余量。 |
| `SSE_HEARTBEAT_SECONDS` | 15 秒 | 等待工作完成时发送 `: heartbeat` 注释，不属于 JSON 事件或模型 token。 |

OpenAI 兼容适配器收到 `[DONE]` 或非空 `finish_reason` 才认定上游正常终止；缺少两者就 EOF 会报错。仅含 usage 的帧可以通过。瞬态故障可在首个内容 delta 前重试，次数受 `AI_PROVIDER_MAX_RETRIES` 限制；畸形帧和截断流不重试。

## 取消与资源归属

页面关闭时中止 fetch。服务最多保留一个待决上游读取；断连、超时或发送失败时，会取消读取、等待其结束，并关闭 guarded、Provider 和内层图迭代器。某项关闭失败仍会尝试其余清理。共享 HTTP 客户端由应用 lifespan 管理，不属于单个轮次。

会话回答边生成边发送，只在输出上限内保留写库所需文本。完整助手回答、工具历史和用量一起提交成功后才发送 `finish`。中断轮次可能只留下已保存的用户消息。

## 代理配置

响应包含 `Cache-Control: no-cache, no-transform` 和 `X-Accel-Buffering: no`。代理需要为两个聊天端点及其 `/api/v1` 别名关闭缓冲。参见[部署](./deployment.md)。
