# Architecture

The repository has no frontend `src/`, pages, client router, stores, composables, UI components, CSS theme or frontend API wrapper. `@vh5/ai-chat` lives elsewhere and consumes this service's legacy SSE endpoint. This repository is the FastAPI half of the backend pair.

```text
Vue / @vh5/ai-chat -> POST /api/ai/chat -> FastAPI -> LLMProvider -> SSE
Go business service -> JWT issuer / product API
JWT user -> /api/conversations/{id}/messages -> ContextBuilder -> direct LLM stream
                                                    | mode=agent / auto trigger
                                                    v
                                               LangGraph -> ToolRegistry
                                                              |
                                                        search_product -> Go
JWT user -> /api/knowledge/documents -> embedding -> PostgreSQL + pgvector
Redis -> request counter, stream quota, conversation lock
```

## Actual module boundaries

| Path | Responsibility |
|---|---|
| `app/main.py` | FastAPI factory, lifespan dependencies, middleware and error envelope |
| `app/api/v1/` | HTTP/SSE routes only: chat, conversations, knowledge, usage and probes |
| `app/schemas/` | Pydantic request/response models and SSE frame types |
| `app/core/` | settings, JWT, errors, logging and observability |
| `app/providers/` | provider-neutral LLM/embedding interfaces and mock/HTTP adapters |
| `app/services/` | context, prompts, model routing, LangGraph, retrieval, quotas and cancellation |
| `app/tools/` | allow-listed Pydantic-validated tools |
| `app/db/` | SQLAlchemy async models, sessions and owner-scoped repositories |
| `alembic/` | PostgreSQL migrations; `evals/` contains a small offline smoke dataset |
| `tests/` | pytest behavior and contract tests |

## Request flow

`create_app()` installs trusted-host and CORS middleware, a request ID, API routes and exception handlers. Lifespan creates the provider, embedding adapter, database, limiter, locks, tool registry and workflow. The legacy `/api/ai/chat` accepts client-supplied `messages[]` and does not persist them. The newer conversation route authorizes a JWT subject, saves the user message, builds a bounded context, then streams or runs the agent. A completed turn saves one assistant message and a `UsageRecord`. A disconnect can leave a saved user message without an assistant reply; consumers must tolerate that state.

The JSON error envelope is `{code,message,data,error,requestId}`. Once SSE headers are sent, errors use an `error` frame. Read [SSE](/sse) for the exact wire format.

## Data and service boundaries

PostgreSQL stores conversations, messages, documents, chunks, embeddings and usage. The migration enables `vector`; SQLite is a local/test fallback with JSON vectors and in-process cosine search. Redis is optional locally; without it, rate counters, stream quota and conversation locks are per process. For multiple replicas, configure Redis. The separate Go service issues JWTs and serves products; this repo does not implement its CRUD. The product tool uses one configured base URL and a fixed `/api/v1/products` path, not a model-selected URL. Live compatibility with a particular Go deployment must be checked separately.

See [Conversations](/conversations), [Agent and RAG](/agent-rag), and [Extending](/extending).
