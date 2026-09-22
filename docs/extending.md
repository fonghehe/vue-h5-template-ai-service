# Extending the service

This Python repository has no Vue pages, menu, frontend permissions, store, composable or UI component workflow. Make those changes in the frontend repository. Here, use these backend boundaries.

## Add an endpoint

Put public Pydantic contracts in `app/schemas/`, add a focused route in `app/api/v1/`, and include it in `app/api/v1/router.py`. Put database rules in `app/db/repositories.py` and orchestration in `app/services/`. Use `AuthenticatedUser` for user-owned data and `get_db_session` for async DB sessions. JSON routes return `ApiResponse(data=..., requestId=request.state.request_id)`; SSE routes use `encode_sse`. Add an Alembic revision for production schema changes.

This excerpt is the real usage route, with imports omitted:

```python
@router.get("/me", response_model=ApiResponse[UsageView])
async def my_usage(request: Request, user: AuthenticatedUser, session: DbSession) -> ApiResponse[UsageView]:
    summary = await UsageRepository(session).summary(user.subject)
    return ApiResponse(data=UsageView.model_validate(summary), requestId=request.state.request_id)
```

## Add provider, model route or tool

`LLMProvider` in `app/providers/base.py` defines `stream`, `complete`, `structured_output` and `tool_calling`. Implement all methods without leaking vendor SDK types, register in `app/providers/factory.py`, and extend `AI_PROVIDER` validation. Embeddings use `EmbeddingProvider`. Task-to-model choices live in `app/services/model_router.py`; versioned prompts live in `app/services/prompts.py`.

Tools subclass `Tool` in `app/tools/base.py`, supply `name`, `description`, Pydantic `input_model` and `execute()`, then register in `app/main.py`. `Tool.run()` validates arguments. Keep outbound destinations fixed and timeouts bounded; never accept model-generated URLs. `ProductSearchTool` is the current pattern.

## Verify

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy app
uv run python -m evals.run
cd docs && npm run docs:typecheck && npm run docs:build
```

Use mock providers/mocked HTTP, not real API keys, in CI. Changes to `ChatRequest`, SSE frames or provider contracts require tests and updates to all three language versions of [SSE](/sse). Preserve `POST /api/ai/chat` and its existing event shape.

Repositories only flush. Put `async with database.sessions.begin()` around service writes and multi-repository work; never commit inside a repository. Register resource closure immediately in lifespan. Use `QuotaStreamingResponse` for SSE admission leases, deadlines, heartbeat comments and cleanup. Keep service signatures free of FastAPI Request/Response. Add domain routers without `/api` in their own prefix; aggregation supplies both `/api` and `/api/v1`.

`stream` returns `AsyncGenerator[str, None]`: implementations must support `aclose()`, forward cancellation to the upstream HTTP stream, and yield incrementally. Register pooled client cleanup in lifespan.

## Feature regression checks

`tests/test_suggestions.py` checks both route prefixes, all three languages, the default, validation failure, response request IDs and independent returned lists. These tests use the application fixture without real model keys. Real PostgreSQL/Redis integration is separately configured in `tests/test_infrastructure.py`; a local unit run may skip those checks.

```bash
uv run pytest tests/test_suggestions.py -q
uv run ruff check .
uv run ruff format --check .
uv run mypy app
```

Curated text lives in `app/services/suggestions.py`; HTTP validation and response wrapping live in `app/api/v1/suggestions.py`. Edit each language deliberately and keep the Literal contract, frontend OpenAPI enum and tests synchronized when adding a locale. The service returns a new list so a caller cannot mutate the shared prompt tuple. It does not personalize prompts from user history.

[API](./api.md)
