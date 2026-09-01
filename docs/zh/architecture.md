# 架构说明

服务是一个应用工厂模式的 FastAPI 应用，进程级依赖在 lifespan 钩子中创建与销毁。

```
app/main.py            应用工厂、lifespan、中间件、异常处理器
app/core/config.py     快速失败配置
app/core/security.py   主体解析（service / user / anonymous）
app/core/errors.py     错误码（与业务服务对齐）
app/core/logging.py    带请求作用域的 JSON / 文本日志
app/providers/         ChatProvider 抽象 + 工厂（mock / openai-compatible）
app/schemas/           请求 + SSE chunk + 信封模型
app/services/          限流器（memory / redis）
app/api/v1/            路由（chat、system）
```

## 请求生命周期

1. **可信主机 + CORS + 请求上下文中间件** 分配关联 ID，并为每个请求输出一条访问日志。
2. **认证** 解析主体：service token → 用户 JWT → anonymous。
3. **处理器** 校验输入、执行限流，然后把供应商片段流式化为 SSE 帧。
4. **异常处理器** 将 `AppError` 与 `RequestValidationError` 映射到共享 JSON 信封。

## 供应商抽象

模型访问封装在 `ChatProvider` 之后：

- `MockChatProvider` —— 预置流，让整条传输链路在开发与测试中离线可用。
- `OpenAICompatibleProvider` —— 通过 `httpx` 访问任意 OpenAI 兼容端点。

工厂（`app/providers/factory.py`）在启动时根据 `AI_PROVIDER` 选择供应商；更换供应商不会改变传输层与前端。

## 流式行为

- 流依次发出 `start`、零个或多个 `delta`、最后 `finish`。
- 处理器在片段之间轮询 `request.is_disconnected()`，浏览器离开时立即中止，避免为无人阅读的 token 付费。
- 流中途失败以 `error` 事件上报，携带客户端安全的信息 —— 供应商内部细节绝不外泄。

## 跨服务身份

`JWT_SECRET`、`JWT_ISSUER`、`JWT_AUDIENCE` 必须与业务服务一致，这样在那边登录过的用户在这里天然已认证。
`SERVICE_TOKEN` 额外允许受信网关代表自己的用户调用。
