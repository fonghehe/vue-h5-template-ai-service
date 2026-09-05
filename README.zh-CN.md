# vue-h5-template-ai-service

[English](./README.md) · [简体中文](./README.zh-CN.md) · [日本語](./README.ja.md)

这是 [vue-h5-template](https://github.com/fonghehe/vue-h5-template) 的 FastAPI AI 助手后端。它保留 `POST /api/ai/chat` 和 `@vh5/ai-chat` 使用的 SSE 契约，并提供用户会话、受限上下文、注册工具、按需使用的 LangGraph Agent、PostgreSQL/pgvector 知识检索，以及用量和可观测性接口。

本仓库是 Python 服务，不是 Vue 前端。兄弟 Go 业务服务负责签发 JWT 和商品 CRUD；本服务通过固定的注册工具调用其商品 API。默认 Mock 模型可离线运行，但不能代表真实模型的回答质量。

## 快速开始

```bash
cp .env.example .env
uv sync --dev
uv run uvicorn app.main:app --reload --port 8001
curl -N http://localhost:8001/api/ai/chat -H 'Content-Type: application/json' -d '{"messages":[{"role":"user","content":"你好"}]}'
```

默认使用 SQLite 和 Mock Provider。本地 PostgreSQL/pgvector + Redis 环境可执行 `docker compose up --build`。Compose 中聊天需要认证，持久化用户资源必须使用用户 JWT；Go 服务需单独启动。

## 文档

[中文开发指南](https://fonghehe.github.io/vue-h5-template-ai-service/zh/)涵盖架构、API、SSE、会话、工具与 RAG、配置、部署和扩展；也可阅读仓库内的[文档源码](./docs/zh/index.md)。本地预览运行 `cd docs && npm ci && npm run docs:dev`。仓库根目录没有 pnpm 文档脚本。

## 检查

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy app
cd docs && npm run docs:typecheck && npm run docs:build
```

## 许可证

[MIT](./LICENSE)
