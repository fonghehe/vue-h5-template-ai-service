# Contributing

Thanks for considering contributing to `vue-h5-template-ai-service`.

## Development environment

You need Python 3.12+ and [`uv`](https://docs.astral.sh/uv/). Everything else is pinned in `uv.lock`.

```bash
uv sync          # install dependencies
make check       # lint + typecheck + test
```

Tests use the offline mock provider and never call a real model, so `make test` is self-contained. The CI job
additionally runs mypy in strict mode and builds the Docker image.

## Workflow

1. Open an issue describing the bug or proposal before starting anything non-trivial.
2. Branch from `main` and keep commits focused and descriptive.
3. Add or update tests for every behavioural change. Run `make check` before pushing.
4. Keep the SSE contract (`start` / `delta` / `finish` / `error`) and the response envelope stable; when you must
   change them, update the `@vh5/ai-chat` consumer and the VitePress docs in `docs/` in the same change.

## Code conventions

- Keep `app/api` a thin transport layer. Provider-specific logic belongs in `app/providers`.
- Every provider implements `ChatProvider`; registering one in `app/providers/factory.py` is all it takes to add a
  vendor.
- Public JSON uses the shared envelope `{ code, message, data, error, requestId }`. Errors never expose stack
  traces, model credentials, or upstream response bodies.
- Forward cancellation to providers; never buffer a complete model response.
- Never commit real user data or API keys.

## Before you open a pull request

- [ ] `make check` passes locally.
- [ ] New behaviour is covered by tests.
- [ ] Docs in `docs/` are updated if the contract changed.
- [ ] No secrets or real user data are committed.

## Code of Conduct

This project follows the [Contributor Covenant](./CODE_OF_CONDUCT.md). By participating, you agree to uphold it.
