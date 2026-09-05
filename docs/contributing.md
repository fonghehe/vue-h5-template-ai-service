# Contributing

```bash
cp .env.example .env
uv sync --dev
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy app
uv run python -m evals.run
```

`pyproject.toml` defines strict mypy and ruff checks. Tests use mocks; no real OpenAI key is needed. For schema changes, add an Alembic migration. See [Extending](/extending) for endpoints, providers and tools.

The VitePress project is in `docs/`: English `/`, Chinese `/zh/`, Japanese `/ja/`. Keep the three versions and sidebar aligned.

```bash
cd docs
npm ci
npm run docs:dev
npm run docs:typecheck
npm run docs:build
```

There is no pnpm docs script at the root. VitePress local search is enabled and build checks internal links. SSE/provider contract changes also need tests and docs updates per `AGENTS.md`. Never commit real JWTs, model credentials or user documents.
