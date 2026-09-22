# FastAPI production engineering review — 2026-10-02

## Baseline and scope

Clean working tree at `cdf6dd3`. Reviewed every Python module in app/, tests/, alembic/ and evals/, pyproject.toml/uv.lock, Docker/Compose, Makefile, environment example, CI and documentation. No requirements files, src/, migrations/ or scripts/ existed. Repository boundaries keep identity issuance and conventional business CRUD in the Go sibling; AI conversations and knowledge are owned here.

Python requirement is >=3.12,<3.15; system Python is 3.14.5 and the uv environment is 3.14.4; container is 3.13. Frozen versions: FastAPI 0.141.1, Starlette 1.6.0, Pydantic 2.13.5, SQLAlchemy 2.0.54, Redis 6.4.0, Uvicorn 0.52.4. uv owns dependency resolution. Initial checks: 79 pytest tests, Ruff lint/format and strict mypy passed. These checks did not prove real Redis/PostgreSQL/provider behavior.

## Existing architecture and strengths

ASGI -> middleware -> API -> providers/services/repositories -> async PostgreSQL/Redis/HTTP. Pydantic v2 schemas, typed async SQLAlchemy models, provider abstraction, owner checks, context budgets, registered tools, LangGraph iterations, pgvector retrieval, shared JWT validation, JSON envelopes and frozen CI already exist. Lifespan and non-root Docker are already used. No global AsyncSession, requests/time.sleep, raw SQL constructed from client sort strings, password storage, token issuance, uploads to local caller-selected paths, WebSockets or task queues exist.

The main shortcomings are behavioral rather than directory layout: the conversation router owns workflow orchestration, repositories independently commit, cancellation is incomplete and async resources are not reliably managed on startup failure. No need for DDD, a generic repository hierarchy, user/order modules or another dependency manager.

## Priorities found before implementation

| Priority | Evidence | Impact / required action |
|---|---|---|
| P0 | services/streaming.py pending anext task lacks finally | Parent cancellation or response closure can leave provider running; cancel, await and close on every exit. |
| P0 | db/repositories.py add_message + UsageRepository.add | Reply and usage commit separately; put final assistant, tools and usage in a service-controlled transaction. |
| P0 | core/config.py production validator | Anonymous production chat is accepted; require auth and distributed Redis, strong JWT/shared secrets. |
| P0 | api/v1/system.py health | Redis URL fragments can include credentials; expose backend name only. |
| P1 | services/agent.py + api/v1/conversations.py | Agent completes entire answer before deltas; separate bounded tool planning from streaming final generation. |
| P1 | providers/base.py, tools/builtin.py | Per-call HTTP clients defeat connection pooling; reuse lifespan-owned clients with bounded timeouts. |
| P1 | services/locks.py | Redis DECR/delete races, fixed conversation lock lifetime, unbounded local lock map; use unique expiring stream leases and bounded whole-stream lifetime below lock expiry. |
| P1 | main.py lifespan | Construction precedes try/finally and sequential close stops on one failure; use AsyncExitStack immediately after each allocation. |
| P1 | api/v1/system.py ready | Readiness ignores database and Redis exceptions become 500; use bounded dependency probes and 503. |
| P2 | api/v1/conversations.py | 341 lines mix HTTP and business flow; move orchestration to services with no Request/Response coupling. |
| P2 | repositories.py lists | Unbounded collection reads; validated pagination, stable ordering and bounded context history. |
| P2 | services/knowledge.py | Synchronous PDF parsing and malformed metadata/vector handling; offload parsing and validate content/metadata. |
| P2 | main.py/logging.py | BaseHTTPMiddleware logs before stream completion; request_scope monkey-patches globally; pure ASGI lifecycle metrics and ContextVar logs. |
| P2 | db/models.py vs initial migration | Four ORM indexes absent from migration; additive corrective revision and schema check. |
| P2 | Dockerfile/.dockerignore | Single stage and local data may enter build context; build/runtime stages, explicit exclusions, graceful shutdown guidance. |
| P3 | billing/RAG/telemetry | Exact provider usage, distributed daily reservations, durable ingestion worker, vector index and exported tracing require explicit operational decisions; document limitations instead of claiming production billing. |

Security review includes JWT signature/algorithm/exp/iat/iss/aud, owner checks, CORS, provider URLs, upload parsing, secret exposure and logs. No claim of a comprehensive external penetration test. Real upstream credentials and user data are never needed for tests.

## Incremental implementation plan

1. Resource lifecycle and streaming: change provider/tool client management, streaming helper, locks, lifespan; add cancellation/startup-failure/lease tests and run targeted checks.
2. Business/DB boundaries: add conversation service, thin routes, flush-only repositories, atomic completed turns, short DB sessions, bounded input/context/lists; add rollback/ownership/pagination tests.
3. Operations: ASGI request context/logs/metrics, readiness, safe settings, versioned aliases, additive migration, multi-stage image/CI integration tests, synchronized English/Chinese/Japanese docs.
4. Verify frozen install, Ruff, strict typing, pytest, SQLite and real PostgreSQL migrations and downgrade/upgrade where available, real Redis concurrency, docs build, package and Docker build, live startup/stream/cancellation. Record environmental limits accurately.

No source deletion or broad directory move. Dependencies remain unchanged unless security evidence requires an update. API compatibility: old paths, camelCase envelope and four base SSE events remain; /api/v1 aliases, optional error code/requestId and SSE comment heartbeats are additive. Pagination bounds unlimited legacy lists (intentional operational behavior change). Agent final text uses real provider streaming; planner text is not the final answer. Production now fails fast on previously accepted unsafe settings. Database evolution is additive; no destructive migration of user data.

## Dependency audit follow-up

Production pip-audit identified 13 known records on the frozen PyJWT 2.13.0 dependency. Upgraded only PyJWT to 2.15.0 and raised its minimum version. Added invalid signature-alphabet and deeply nested header regressions; HS256-only validation and fresh per-call options remain. This is a dependency finding, not evidence that all listed JWKS/algorithm paths are used by this service. Final audit results are in ENGINEERING_REPORT.md.

## References

- https://github.com/jpadilla/pyjwt/releases/tag/2.15.0 — patched JWT dependency.
- https://www.python-httpx.org/async/ — scoped clients, connection pooling and stream closure.
- https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html — task-local sessions and explicit engine disposal.

Final validation and remaining boundaries are recorded in ENGINEERING_REPORT.md.
