# 贡献指南

## 本地检查

使用 Python 3.12–3.14 和 uv。默认测试使用隔离 SQLite、Mock 模型与 HTTP，无需真实模型凭据；基础设施测试未配置时会跳过。

```bash
uv sync --frozen --dev
uv run ruff check .
uv run ruff format --check .
uv run mypy app
uv run pytest
uv run python -m evals.run
```

## 隔离集成测试

使用可丢弃的 PostgreSQL 实例，安装 pgvector 并建立 `vh5_ai_test` 数据库；Redis 使用隔离实例的 DB 15。先将下列环境变量指向这些实例，不要连接业务数据。

```bash
export AI_TEST_DATABASE_URL='postgresql+asyncpg://<user>:<password>@<isolated-host>:5432/vh5_ai_test'
export AI_TEST_REDIS_URL='redis://<isolated-host>:6379/15'
DATABASE_URL="$AI_TEST_DATABASE_URL" DATABASE_AUTO_CREATE=false uv run alembic upgrade head
uv run pytest -m integration
```

修改数据库结构时运行 `uv run alembic upgrade head` 和 `uv run alembic check`。包含 `downgrade base` 的迁移往返只能在可丢弃数据库执行。测试会拒绝其他数据库名／Redis DB 编号，但命名本身不代表环境已隔离。

## 本地测量

```bash
uv run python -m scripts.benchmark_hot_paths
```

基准使用合成输入、7 次计时样本和 `tracemalloc` 分配峰值。对比时在独立检出目录使用相同脚本、Python 和机器，不要重置含改动的工作区。这些微基准不测量真实模型或生产吞吐。

## 文档

在 `docs/` 目录运行以下命令。文档开发服务器不启动 API；构建会校验内部页面链接。英文、中文、日文页面保持同步。

```bash
npm ci
npm run docs:dev
# Validation before publishing:
npm run docs:typecheck
npm run docs:build
```

## 提交 PR 前

遵循 `AGENTS.md`，测试变化的行为，保持 Provider/SSE 契约稳定，由 Service 控制事务，资源创建后立即登记清理。契约变化需同步三种语言文档，扩展步骤见[扩展指南](./extending.md)。不要提交凭据、真实 JWT 或用户文档。

CI 配置了 PostgreSQL/pgvector、Redis、迁移往返、Python 检查、包／镜像构建和依赖审计。文档工作流先检查并构建 VitePress，再部署 Pages。本地通过不代表远端 CI 或部署已经完成。
