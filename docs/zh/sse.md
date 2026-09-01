# SSE 契约

`POST /api/ai/chat` 返回 `text/event-stream`，其事件正是 `@vh5/ai-chat` 消费的 `ChatChunk` 联合类型。

| `type` | 字段 | 含义 |
|---|---|---|
| `start` | `id` | 流已接受；携带会话 id。 |
| `delta` | `delta` | 一段文本片段；按顺序拼接。 |
| `finish` | `reason` | 终止事件：`stop`、`abort` 或 `error`。 |
| `error` | `message` | 流开始后失败；客户端会抛出。 |

每个帧都是一行 `data:`，携带紧凑 JSON：

```text
data: {"type":"start","id":"conversation-9f2c…"}
data: {"type":"delta","delta":"Streaming "}
data: {"type":"finish","reason":"stop"}
```

## 终止原因

- `stop` —— 供应商正常结束。
- `abort` —— 客户端在流中途断开；服务立即停止，避免为无人阅读的 token 付费。
- `error` —— 供客户端库通过 `FinishChunk` 的 reason 上报失败；服务本身此时发出的是 `error` 事件。

## 错误处理 —— 流开始前 vs 流进行中

- **首个字节之前**发生的错误，以普通 JSON 错误信封返回，附带正确的 HTTP 状态码与应用错误码。
- **流进行中**发生的错误，则变成 `error` 事件，因为 HTTP 状态码已经发送。

## 响应头

响应会设置阻止中间层缓冲流的头：

```
Cache-Control: no-cache, no-transform
Connection: keep-alive
X-Accel-Buffering: no
```

如果用 nginx 反向代理，还需设置 `proxy_buffering off;` —— 见 [部署指南](/zh/deployment)。
