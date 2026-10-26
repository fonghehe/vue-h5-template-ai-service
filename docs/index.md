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


## Start here

Use [Quick start](./quickstart.md) to run the mock service, [API](./api.md) to connect a client, and [Deployment](./deployment.md) to prepare an environment. Go issues access JWTs; this service owns AI conversations and document retrieval. Mock responses verify the integration path, not real model quality.
