# Conversations and context

The legacy `POST /api/ai/chat` remains stateless for `@vh5/ai-chat`. Use `/api/conversations` when the server must own history. All persistent endpoints require a **user JWT** minted by the Go service; service-token and anonymous principals cannot own conversations.

## Send a turn

```bash
curl -s http://localhost:8001/api/conversations -H "Authorization: Bearer $AI_USER_JWT" -H 'Content-Type: application/json' -d '{"title":"Shopping help"}'
# Copy data.id into AI_CONVERSATION_ID:
curl -N "http://localhost:8001/api/conversations/$AI_CONVERSATION_ID/messages" -H "Authorization: Bearer $AI_USER_JWT" -H 'Content-Type: application/json' -d '{"content":"Hello","mode":"chat","useRag":false}'
```

`mode` is `auto` (default), `chat`, or `agent`. The `auto` selector in `app/services/conversations.py` is a small keyword heuristic for products, calculation and time, not a general intent classifier. `GET /api/conversations/{id}` returns ordered messages, summary and citations. `GET /api/conversations` lists headers. `DELETE` removes an owned conversation and its messages.

## Context and storage

`ContextBuilder` in `app/services/context.py` combines the versioned system prompt, saved summary, optional retrieved text/tool results and recent messages. It estimates tokens at roughly one per three characters plus message overhead; this is **not** the provider tokenizer. When history does not fit `AI_CONTEXT_TOKEN_BUDGET`, older messages are summarized via `LLMProvider.complete()` and saved in `conversation.summary`. Prompt/retrieval text may be truncated. Tests exercise 100 history messages.

Assistant, tools and usage are atomic on completion. Direct/final-stream token counts are estimates; agent planning uses provider usage when available. Daily limits check completed recorded turns and can overshoot under concurrent requests; legacy chat and interrupted turns are not recorded. This is an admission threshold, not an exact billing or prepaid reservation system.

Collections accept `page` (1–100000) and `page_size` (1–100, default 50), preserving the existing list envelope. Conversation details return the latest 100 messages by default; use `page_size` and `before=<sequence>` for earlier pages. Message responses expose `sequence`. Context loads at most 200 recent messages, bounds summarization input, and preserves the newest user turn or rejects it if too large. Persistent message content is limited to 20000 characters and the configured context budget. Old `/api/*` paths remain; every business route also has an `/api/v1/*` alias.
