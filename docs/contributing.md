# Contributing

Thanks for your interest in contributing. This document covers the workflow; behaviour expectations live in
[CODE_OF_CONDUCT.md](https://github.com/fonghehe/vue-h5-template-ai-service/blob/main/CODE_OF_CONDUCT.md).

## Setup

```bash
git clone https://github.com/fonghehe/vue-h5-template-ai-service.git
cd vue-h5-template-ai-service
cp .env.example .env
uv sync
```

Requires Python 3.12–3.14 and [uv](https://docs.astral.sh/uv/).

## Development commands

```bash
make check     # lint + typecheck + test
make lint      # ruff check + ruff format --check
make typecheck # mypy --strict
make test      # pytest
make format    # ruff format + ruff check --fix
```

## Code style

- Formatting and linting are enforced by **ruff** (config in `pyproject.toml`).
- Type checking runs **mypy in strict mode**.
- Schemas in `app/schemas/` are the contract with `@vh5/ai-chat` — renaming a field is a breaking change.

## Adding a provider

1. Implement `ChatProvider` in `app/providers/`.
2. Register it in `app/providers/factory.py`.
3. Add tests under `tests/`.
4. Update the `AI_PROVIDER` docs in the configuration reference.

## Pull request checklist

1. Add or update tests.
2. Run `make check` locally and keep it green.
3. Keep the SSE event shapes and the response envelope unchanged unless deliberately versioning them.
4. Update the docs when the surface changes.

## Releasing

Bump the version in `pyproject.toml` and tag the release.
