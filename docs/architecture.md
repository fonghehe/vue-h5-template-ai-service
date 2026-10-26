# Architecture

The Vue client reads SSE from this FastAPI service. The sibling Go service issues access JWTs and owns product APIs. This service validates those tokens, stores AI conversations and documents, and optionally calls registered tools.

```text
Vue -> FastAPI routes -> Services -> LLM / Embedding providers
                            |----> Repositories -> PostgreSQL / pgvector
                            |----> Agent -> ToolRegistry -> Go product API
                            `----> Redis: counters / stream leases / locks
Go -> access JWT -> FastAPI authentication
```

## Module responsibilities

| Path | Responsibility |
|---|---|
| `app/main.py` | Application factory and lifespan resources |
| `app/api/` | HTTP/SSE transport and dependencies |
| `app/schemas/` | Public request, response and event contracts |
| `app/services/` | Conversation, context, agent, retrieval and quota orchestration |
| `app/providers/` | Provider-neutral LLM/embedding interfaces and adapters |
| `app/tools/` | Registered tools and argument validation |
| `app/db/` | Async sessions, models and owner-scoped repositories |
| `app/core/` | Settings, JWT validation, errors and observability |
| `alembic/`, `tests/`, `evals/` | Migrations, behavior tests and offline smoke evaluation |

## Transactions and resources

Repositories flush changes; services decide when to commit or roll back. Conversation requests save the user message in a short transaction, build context and generate without holding that transaction open, then commit the completed reply and usage together. See [Conversations](./conversations.md).

Lifespan registers cleanup immediately after resource creation, including partial startup failure. HTTP and Redis clients are shared; sessions and response streams have request/turn scope. SSE wrappers explicitly close nested iterators. See [SSE](./sse.md).

## Storage and replica coordination

PostgreSQL/pgvector stores conversations, documents, vectors and usage. SQLite is the local/test fallback. Redis shares request counts, concurrent-stream leases and conversation locks across replicas; without it, coordination is process-local. Staging/production require Redis and PostgreSQL.

The product tool calls the fixed `/api/v1/products` path under the configured Go base URL. Validate the target deployment’s token and `X-User-ID` policy separately. See [Agent and RAG](./agent-rag.md) and [Extending](./extending.md).
