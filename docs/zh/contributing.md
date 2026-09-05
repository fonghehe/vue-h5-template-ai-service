# 贡献指南

```bash
cp .env.example .env
uv sync --dev
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy app
uv run python -m evals.run
```

`pyproject.toml` 定义严格 mypy 和 ruff；测试使用 Mock，不需要真实 OpenAI Key。数据库 schema 变动需 Alembic 迁移。接口、Provider 和工具扩展方法见[扩展指南](/zh/extending)。

VitePress 在 `docs/`：英文 `/`、中文 `/zh/`、日文 `/ja/`。保持三语内容及导航同步。

```bash
cd docs
npm ci
npm run docs:dev
npm run docs:typecheck
npm run docs:build
```

根目录没有 pnpm docs 脚本。VitePress 已启用本地搜索，构建会检查内部链接。SSE/Provider 契约变更还需按 `AGENTS.md` 更新测试和文档。不要提交真实 JWT、模型密钥或用户文档。
