# Quick start

Run the AI service locally with the offline mock provider — no API key required.

## Prerequisites

- **Python 3.12–3.14**
- **[uv](https://docs.astral.sh/uv/)** — the package and environment manager.

## Install and run

```bash
cp .env.example .env
uv sync                 # install dependencies from the frozen lockfile
make dev                # run with autoreload on :8001
```

`make dev` runs `uv run uvicorn app.main:app --reload --port 8001`. With the default `AI_PROVIDER=mock` the service
answers with a canned stream, so you can test the whole transport without an upstream account.

## Try it

```bash
curl -N http://localhost:8001/api/ai/chat \
  -H 'Content-Type: application/json' \
  -d '{"messages":[{"role":"user","content":"Why is streaming useful?"}]}'
```

```text
data: {"type":"start","id":"conversation-9f2c…"}
data: {"type":"delta","delta":"Streaming "}
data: {"type":"delta","delta":"keeps the UI honest. "}
data: {"type":"finish","reason":"stop"}
```

Interactive OpenAPI docs are at `http://localhost:8001/docs`.

## Switch to a real provider

Any OpenAI-compatible endpoint works (OpenAI, Azure OpenAI, Together, Groq, Ollama, vLLM):

```bash
AI_PROVIDER=openai-compatible
AI_BASE_URL=https://api.openai.com/v1
AI_API_KEY=sk-…
AI_MODEL=gpt-4o-mini
```

See [Configuration](/configuration) for the full list.

## Development loop

```bash
make check     # lint + typecheck + test
make test      # pytest
make typecheck # mypy --strict
```

## Next steps

- [The SSE contract](/sse) — the exact event shapes.
- [API reference](/api) — endpoints and the response envelope.
- [Deployment](/deployment) — production notes, especially around proxy buffering.
