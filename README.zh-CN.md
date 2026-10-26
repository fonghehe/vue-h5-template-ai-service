# vue-h5-template-ai-service

[English](./README.md) · [简体中文](./README.zh-CN.md) · [日本語](./README.ja.md)

[vue-h5-template](https://github.com/fonghehe/vue-h5-template) 的 FastAPI AI 后端，提供 SSE 增量聊天、会话保存、注册工具和文档检索（RAG）。兄弟 Go 服务负责签发 JWT 和提供商品 API。

## 本地启动

需要 Python 3.12–3.14 和 uv。默认使用 SQLite 与离线 Mock 模型，无需模型密钥。启动后在另一个终端运行 curl。

```bash
cp .env.example .env
uv sync --frozen --dev
uv run uvicorn app.main:app --reload --port 8001
```

```bash
curl -N http://localhost:8001/api/ai/chat \
  -H 'Content-Type: application/json' \
  -d '{"messages":[{"role":"user","content":"Hello"}]}'
```

本地模式的持久化会话和知识库接口也需要 Go 签发的用户 access JWT。Mock 测试不能证明真实模型质量或生产容量。

## 继续阅读

- [本地运行](./docs/zh/quickstart.md)
- [API 与认证](./docs/zh/api.md)
- [流式协议](./docs/zh/sse.md)
- [配置参考](./docs/zh/configuration.md)
- [部署指南](./docs/zh/deployment.md)
- [开发与测试](./docs/zh/contributing.md)

[VitePress](https://fonghehe.github.io/vue-h5-template-ai-service/zh/) · [MIT](./LICENSE)
