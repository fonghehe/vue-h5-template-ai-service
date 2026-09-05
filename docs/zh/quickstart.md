# 快速开始

## 环境

API 使用 Python 3.12–3.14 和 uv。只有 VitePress 文档需要 Node.js/npm。根目录是 `pyproject.toml` + `uv.lock` 的 Python 项目；`package.json` / `package-lock.json` 位于 `docs/`，根目录没有 pnpm 文档脚本。

## 离线启动

```bash
cp .env.example .env
uv sync --dev
uv run uvicorn app.main:app --reload --port 8001
```

默认使用 Mock Provider 和 `.data/ai-service.db` SQLite 文件，启动时自动建表；这是本地开发回退方案，不是生产 PostgreSQL/pgvector。启用 `DOCS_ENABLED` 时可打开 `http://localhost:8001/docs`。

```bash
curl -N http://localhost:8001/api/ai/chat -H 'Content-Type: application/json' -d '{"messages":[{"role":"user","content":"你好"}]}'
```

响应为 `start`、若干 `delta`、`finish`。Mock 返回预置文本，并不会真正回答问题。

## 持久化会话

即使 `AI_AUTH_REQUIRED=false`，会话与知识库接口仍要求由 Go 业务服务签发的**用户 JWT**；`SERVICE_TOKEN` 不能访问用户数据。本服务不签发 JWT。拿到有效令牌后：

```bash
curl -s http://localhost:8001/api/conversations -H "Authorization: Bearer $AI_USER_JWT" -H 'Content-Type: application/json' -d '{"title":"第一次对话"}'
```

将返回的 `data.id` 用于 `POST /api/conversations/{id}/messages`。完整流程见[会话与上下文](/zh/conversations)。

## Compose 与检查

`docker compose up --build` 会启动 API、Redis、PostgreSQL/pgvector，并先运行 Alembic；Compose 设置 `AI_AUTH_REQUIRED=true`，所以上面的匿名 curl 在 Compose 中会得到 401。Go 服务不包含在本 Compose 中。参见[部署](/zh/deployment)。

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy app
cd docs
npm ci
npm run docs:dev
npm run docs:build
```

VitePress 开发服务器不会启动 API。配置详情见[配置参考](/zh/configuration)。
