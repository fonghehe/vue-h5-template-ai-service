# 快速开始

用离线 mock provider 在本地把 AI 服务跑起来 —— 无需 API Key。

## 前置条件

- **Python 3.12–3.14**
- **[uv](https://docs.astral.sh/uv/)** —— 包与环境管理器。

## 安装并运行

```bash
cp .env.example .env
uv sync       # 从冻结的 lockfile 安装依赖
make dev      # 以 autoreload 模式在 :8001 运行
```

`make dev` 执行 `uv run uvicorn app.main:app --reload --port 8001`。默认 `AI_PROVIDER=mock` 时服务返回预置的
流式内容，无需上游账号即可验证整条传输链路。

## 试用

```bash
curl -N http://localhost:8001/api/ai/chat \
  -H 'Content-Type: application/json' \
  -d '{"messages":[{"role":"user","content":"为什么流式很有用？"}]}'
```

```text
data: {"type":"start","id":"conversation-9f2c…"}
data: {"type":"delta","delta":"Streaming "}
data: {"type":"delta","delta":"keeps the UI honest. "}
data: {"type":"finish","reason":"stop"}
```

交互式 OpenAPI 文档在 `http://localhost:8001/docs`。

## 切换到真实供应商

任意 OpenAI 兼容端点均可（OpenAI、Azure OpenAI、Together、Groq、Ollama、vLLM）：

```bash
AI_PROVIDER=openai-compatible
AI_BASE_URL=https://api.openai.com/v1
AI_API_KEY=sk-…
AI_MODEL=gpt-4o-mini
```

完整清单见 [配置参考](/zh/configuration)。

## 开发循环

```bash
make check     # lint + typecheck + test
make test      # pytest
make typecheck # mypy --strict
```

## 下一步

- [SSE 契约](/zh/sse) —— 精确的事件结构。
- [API 参考](/zh/api) —— 端点与响应信封。
- [部署指南](/zh/deployment) —— 生产注意事项，尤其是代理缓冲。
