# vue-h5-template-ai-service

[English](./README.md) · [简体中文](./README.zh-CN.md) · [日本語](./README.ja.md)

这是 [vue-h5-template](https://github.com/fonghehe/vue-h5-template) 的 FastAPI AI 助手后端。它保留 `POST /api/ai/chat` 和 `@vh5/ai-chat` 使用的 SSE 契约，并提供用户会话、受限上下文、注册工具、按需使用的 LangGraph Agent、PostgreSQL/pgvector 知识检索，以及用量和可观测性接口。

本仓库是 Python 服务，不是 Vue 前端。兄弟 Go 业务服务负责签发 JWT 和商品 CRUD；本服务通过固定的注册工具调用其商品 API。默认 Mock 模型可离线运行，但不能代表真实模型的回答质量。

## 快速开始

```bash
cp .env.example .env
uv sync --frozen --dev
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

## 架构与维护

支持 Python 3.12–3.14，uv 锁定 FastAPI/Pydantic v2、SQLAlchemy 2 异步、Alembic、Redis、httpx。HTTP 路由调用小型 Service；Repository 只 flush，Service 控制事务。lifespan 在启动失败时也会关闭连接池。支持旧 `/api/*` 和 `/api/v1/*`。详见[审计与改造方案](./ARCHITECTURE_REVIEW.md)及[实际验收报告](./ENGINEERING_REPORT.md)。

## 数据库与部署

本地 SQLite 可自动建表；生产使用 PostgreSQL/pgvector、Redis 和显式迁移：

```bash
uv run alembic upgrade head
uv run alembic check
curl http://localhost:8001/health
curl http://localhost:8001/ready
```

启动前配置环境变量。staging/production 强制认证、强密钥、Redis、明确的主机白名单、JSON 日志、关闭文档和 `DATABASE_AUTO_CREATE=false`。每次部署先单独执行迁移，再启动副本。多阶段镜像以非 root 用户运行；代理需关闭 SSE 缓冲、限定受信任代理 IP，关闭宽限期应大于流的截止时间。具体配置见[部署指南](./docs/zh/deployment.md)。JWT 仍由 Go 服务签发，此处不重复建设用户、订单或密码系统。

测试默认使用隔离 SQLite、Mock HTTP/模型。真实集成测试要求 `AI_TEST_DATABASE_URL` 指向可丢弃的 `vh5_ai_test` 数据库，`AI_TEST_REDIS_URL` 使用 Redis DB 15，运行 `uv run pytest -m integration`。CI 提供这些基础设施并验证迁移往返。真实模型质量、Go 联调、追踪 exporter、精确计费均有明确的验证边界。

## 许可证

[MIT](./LICENSE)
