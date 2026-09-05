---
layout: home

hero:
  name: "vue-h5-template-ai-service"
  text: "AI assistant backend"
  tagline: FastAPI service for persistent conversations, bounded context and compatible SSE streaming.
  actions:
    - theme: brand
      text: Quick start
      link: /quickstart
    - theme: alt
      text: Architecture
      link: /architecture
    - theme: alt
      text: API
      link: /api

features:
  - title: Existing client contract
    details: POST /api/ai/chat keeps the start, delta, finish and error SSE frames used by @vh5/ai-chat.
  - title: Server-owned conversations
    details: JWT-scoped messages, summaries, usage records and per-conversation serialization.
  - title: Bounded agent path
    details: LangGraph is used for registered tools; ordinary chat stays on a direct async stream.
  - title: Lightweight knowledge base
    details: Text, Markdown and PDF ingestion with pgvector retrieval in PostgreSQL and citations.
---

## What this repository owns

This is a Python service, not a Vue application. The sibling Go business service owns login, token issuance and product CRUD. This service validates its JWTs, owns AI conversations, and calls the Go product API only through a registered tool. There is no `src/`, page router, frontend store, browser theme, i18n or mobile layout in this repository.

Start with [local setup](/quickstart), then read [architecture](/architecture) and the [API reference](/api). The offline mock answers deterministically; it does **not** demonstrate real model quality or validate the live Go integration.
