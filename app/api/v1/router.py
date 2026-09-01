"""API router aggregation.

Routes are grouped under `/api` so that a reverse proxy can forward a single
path prefix to this service. The chat endpoint itself sits at `/api/ai/chat`,
matching the default endpoint of `FetchChatProvider` in `@vh5/ai-chat`.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import chat, system

api_router = APIRouter()
api_router.include_router(system.router, prefix="", tags=["system"])
api_router.include_router(chat.router)

__all__ = ["api_router"]
