# Contributing

## Local checks

Use Python 3.12–3.14 and uv. The default suite uses isolated SQLite and mocked models/HTTP. It does not need real model credentials; infrastructure cases skip unless configured.

```bash
uv sync --frozen --dev
uv run ruff check .
uv run ruff format --check .
uv run mypy app
uv run pytest
uv run python -m evals.run
```

## Isolated infrastructure tests

Use a disposable PostgreSQL instance with pgvector and database name `vh5_ai_test`, plus an isolated Redis instance using DB 15. Set the following variables to those instances before running. Never point them at business data.

```bash
export AI_TEST_DATABASE_URL='postgresql+asyncpg://<user>:<password>@<isolated-host>:5432/vh5_ai_test'
export AI_TEST_REDIS_URL='redis://<isolated-host>:6379/15'
DATABASE_URL="$AI_TEST_DATABASE_URL" DATABASE_AUTO_CREATE=false uv run alembic upgrade head
uv run pytest -m integration
```

Run `uv run alembic upgrade head` and `uv run alembic check` for schema changes. Migration round trips, including `downgrade base`, belong only on a disposable database. Tests reject other database names/Redis DB numbers; those names alone do not establish isolation.

## Local measurements

```bash
uv run python -m scripts.benchmark_hot_paths
```

The benchmark uses synthetic inputs, seven timing samples and `tracemalloc` allocation peaks. Compare the same script, Python and machine in separate checkouts; do not reset a working tree containing changes. These microbenchmarks do not measure live models or production throughput.

## Documentation

Run these commands in `docs/`. The dev server is separate from the API; build validates internal page links. Keep English, Chinese and Japanese pages aligned.

```bash
npm ci
npm run docs:dev
# Validation before publishing:
npm run docs:typecheck
npm run docs:build
```

## Before a pull request

Follow `AGENTS.md`. Test changed behavior, keep provider/SSE contracts stable, let services own transactions, and register resource cleanup immediately. Update all three documentation languages for contract changes. See [Extending](./extending.md). Do not commit credentials, real JWTs or user documents.

CI configures PostgreSQL/pgvector and Redis, migration round trips, Python checks, package/image builds and dependency auditing. The docs workflow typechecks/builds VitePress before Pages deployment. A local pass is not proof of remote CI or deployment.
