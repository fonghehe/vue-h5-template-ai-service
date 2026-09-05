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
