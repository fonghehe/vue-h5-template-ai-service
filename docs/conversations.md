# Conversations and context

The legacy `POST /api/ai/chat` remains stateless for `@vh5/ai-chat`. Use `/api/conversations` when the server must own history. All persistent endpoints require a **user JWT** minted by the Go service; service-token and anonymous principals cannot own conversations.

## Send a turn

```bash
curl -s http://localhost:8001/api/conversations -H "Authorization: Bearer $AI_USER_JWT" -H 'Content-Type: application/json' -d '{"title":"Shopping help"}'
# Copy data.id into AI_CONVERSATION_ID:
curl -N "http://localhost:8001/api/conversations/$AI_CONVERSATION_ID/messages" -H "Authorization: Bearer $AI_USER_JWT" -H 'Content-Type: application/json' -d '{"content":"Hello","mode":"chat","useRag":false}'
```

`mode` is `auto` (default), `chat`, or `agent`. The `auto` selector in `app/api/v1/conversations.py` is a small keyword heuristic for products, calculation and time, not a general intent classifier. `GET /api/conversations/{id}` returns ordered messages, summary and citations. `GET /api/conversations` lists headers. `DELETE` removes an owned conversation and its messages.

## Context and storage

`ContextBuilder` in `app/services/context.py` combines the versioned system prompt, saved summary, optional retrieved text/tool results and recent messages. It estimates tokens at roughly one per three characters plus message overhead; this is **not** the provider tokenizer. When history does not fit `AI_CONTEXT_TOKEN_BUDGET`, older messages are summarized via `LLMProvider.complete()` and saved in `conversation.summary`. Prompt/retrieval text may be truncated. Tests exercise 100 history messages.

A conversation-level lock serializes turns for the same ID; Redis coordinates across replicas, otherwise locks are process-local. A completed turn saves an assistant message and `UsageRecord`; a client disconnect can leave the already-saved user message without an assistant response. `GET /api/usage/me` groups successful persistent turns by model, conversation and date. Legacy chat does not create usage rows. Direct-stream token counts are estimates; agent counts come from provider results when available. This is cost awareness, not billing.
