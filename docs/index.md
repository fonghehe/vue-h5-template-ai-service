---
layout: home

hero:
  name: "ai-service"
  text: "Streaming AI for vue-h5-template"
  tagline: A provider-neutral AI service that exchanges a typed message list for a Server-Sent Events stream.
  actions:
    - theme: brand
      text: Quick start
      link: /quickstart
    - theme: alt
      text: The SSE contract
      link: /sse
    - theme: alt
      text: View on GitHub
      link: https://github.com/fonghehe/vue-h5-template-ai-service

features:
  - title: Provider-neutral
    details: Model access sits behind a <code>ChatProvider</code> interface — the offline mock and any OpenAI-compatible endpoint are interchangeable without touching the transport.
  - title: SSE out of the box
    details: Emits <code>start</code>, <code>delta</code> and <code>finish</code> events that <code>@vh5/ai-chat</code> consumes directly.
  - title: Shared identity
    details: Validates the same JWTs minted by the Go business service, so a logged-in user is already authenticated here.
  - title: Ops-ready
    details: Non-root Docker image, health/readiness probes, Redis-backed rate limiting, structured logs, and GitHub Actions CI.
---

## Why a separate service?

This is the streaming half of the vue-h5-template backend pair:

| | Business service (Go) | AI service (Python) |
|---|---|---|
| Workload | Short, transactional CRUD | Long-lived streaming |
| Scaling | Request rate | Concurrent streams |
| Failure mode | Database latency | Upstream model latency |

Keeping them apart means a slow model provider can never exhaust the connection pool that serves login and the
catalogue.

## The pipeline

```
Vue H5 app ──POST /api/ai/chat──▶ ai-service ──▶ mock provider        (development)
        ◀── SSE: start/delta/finish ──┘         └─▶ OpenAI-compatible  (production)
```
