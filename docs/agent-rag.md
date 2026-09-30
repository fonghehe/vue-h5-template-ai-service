# Agent, tools and RAG

## Agent route

`mode="chat"` uses a direct provider stream. `mode="agent"` runs bounded LangGraph tool planning; auto mode uses a product/calculation/time keyword heuristic in `app/services/conversations.py`. The graph chooses registered tools and executes them, then the provider streams the final answer. Planner calls are capped at 256 output tokens; they are not displayed. The final answer is never sliced from a completed model result. `AGENT_MAX_ITERATIONS`, the whole-stream deadline and output cap bound work.

## Tool boundary

`ToolRegistry` in `app/tools/base.py` exposes only registered names and Pydantic-validates arguments. `get_current_time` returns UTC, `calculator` evaluates restricted arithmetic AST, and `search_product` sends a fixed GET to `BUSINESS_SERVICE_URL/api/v1/products` with `q`, optional `maxPrice`, `limit`, `X-User-ID` and a bearer token when configured. No model-selected URL is accepted. The Go service is external to this Compose stack; validate its exact route and trust policy in your deployment. Prompt instructions treat retrieved/tool text as untrusted, but cannot guarantee immunity to prompt injection.

## Knowledge flow

`POST /api/knowledge/documents` accepts multipart `file` and optional JSON-string `metadata`. `KnowledgeService` parses UTF-8 `.txt`/`.md` or extractable PDF text, chunks by overlapping characters, embeds and saves it. No OCR exists for scanned PDFs. Upload size defaults to 5 MB. PostgreSQL/pgvector runs owner-scoped cosine top-K; the SQLite fallback ranks in process. Mock embeddings are deterministic hashing for tests, not production semantic retrieval.

With `useRag=true`, a turn embeds the query, retrieves owner-scoped chunks, adds their text to context and emits `sources` with `documentId`, `chunkId`, `title`. A citation identifies retrieved material; it does not prove every answer claim. `assistant.rag` v1 asks for grounded answers.

## Structured output and evaluation

`LLMProvider.structured_output()` validates against a Pydantic model; the HTTP adapter retries invalid JSON once. `ProductRecommendation` in `app/schemas/knowledge.py` is an example schema, not a public API response. `evals/run.py` is a small offline smoke script: one calculator case and non-empty mock completions, **not** a quantitative RAG benchmark. Pytest adds targeted retrieval/tool/schema checks. Green smoke results do not establish live model quality.

Upload metadata must be a JSON object. Parsing runs in a bounded worker thread, PDF signatures are validated, filenames are reduced to basenames, extracted text/chunk counts are capped, and embedding requests use batches of 64. Document and chunks commit together; SQLite enables foreign-key cascades. Untrusted PDFs with stringent isolation requirements need a separate resource-limited parsing worker.

## SQLite fallback ranking

PostgreSQL continues to use its existing vector search. The SQLite fallback scores owner-scoped candidates and retains only the best `top_k` result objects with `heapq.nlargest`, rather than building and sorting a second full result list. Equal scores retain candidate order; citations and ownership filtering are unchanged. Ranking retains O(K) results and costs O(N log K) when K is small. Repository candidate loading and embedding computation still contribute their own memory and latency; this is not streaming database retrieval or an end-to-end model benchmark.
