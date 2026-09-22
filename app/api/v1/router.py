"""API router aggregation.

Routes are grouped under `/api` so that a reverse proxy can forward a single
path prefix to this service. The chat endpoint itself sits at `/api/ai/chat`,
matching the default endpoint of `FetchChatProvider` in `@vh5/ai-chat`.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import chat, conversations, knowledge, suggestions, system, usage

api_router = APIRouter()
api_router.include_router(system.router)
for prefix in ("/api", "/api/v1"):
    for domain_router in (chat.router, conversations.router, knowledge.router, usage.router, suggestions.router):
        api_router.include_router(domain_router, prefix=prefix)

__all__ = ["api_router"]
