# Agent, tools and RAG

## Agent route

`mode="chat"` uses a direct provider stream. `mode="agent"` runs LangGraph; `auto` runs it for the route's product/calculation/time keyword heuristic. `app/services/agent.py` builds `START -> classify -> agent -> (tool -> agent)* -> END`. The current `classify` node only labels the path; it is not model classification. `AGENT_MAX_ITERATIONS` bounds turns. Graph updates produce tool events, but the final answer is sliced into `delta` frames **after** the graph returns, not streamed token by token.

## Tool boundary

`ToolRegistry` in `app/tools/base.py` exposes only registered names and Pydantic-validates arguments. `get_current_time` returns UTC, `calculator` evaluates restricted arithmetic AST, and `search_product` sends a fixed GET to `BUSINESS_SERVICE_URL/api/v1/products` with `q`, optional `maxPrice`, `limit`, `X-User-ID` and a bearer token when configured. No model-selected URL is accepted. The Go service is external to this Compose stack; validate its exact route and trust policy in your deployment. Prompt instructions treat retrieved/tool text as untrusted, but cannot guarantee immunity to prompt injection.

## Knowledge flow

`POST /api/knowledge/documents` accepts multipart `file` and optional JSON-string `metadata`. `KnowledgeService` parses UTF-8 `.txt`/`.md` or extractable PDF text, chunks by overlapping characters, embeds and saves it. No OCR exists for scanned PDFs. Upload size defaults to 5 MB. PostgreSQL/pgvector runs owner-scoped cosine top-K; the SQLite fallback ranks in process. Mock embeddings are deterministic hashing for tests, not production semantic retrieval.

With `useRag=true`, a turn embeds the query, retrieves owner-scoped chunks, adds their text to context and emits `sources` with `documentId`, `chunkId`, `title`. A citation identifies retrieved material; it does not prove every answer claim. `assistant.rag` v1 asks for grounded answers.

## Structured output and evaluation

`LLMProvider.structured_output()` validates against a Pydantic model; the HTTP adapter retries invalid JSON once. `ProductRecommendation` in `app/schemas/knowledge.py` is an example schema, not a public API response. `evals/run.py` is a small offline smoke script: one calculator case and non-empty mock completions, **not** a quantitative RAG benchmark. Pytest adds targeted retrieval/tool/schema checks. Green smoke results do not establish live model quality.
