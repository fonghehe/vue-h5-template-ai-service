"""Cost-awareness endpoint for the authenticated user."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import AuthenticatedUser
from app.db.repositories import UsageRepository
from app.db.session import get_db_session
from app.schemas.conversation import UsageView
from app.schemas.envelope import ApiResponse

router = APIRouter(prefix="/api/usage", tags=["usage"])
DbSession = Annotated[AsyncSession, Depends(get_db_session)]


@router.get("/me", response_model=ApiResponse[UsageView])
async def my_usage(request: Request, user: AuthenticatedUser, session: DbSession) -> ApiResponse[UsageView]:
    summary = await UsageRepository(session).summary(user.subject)
    return ApiResponse(data=UsageView.model_validate(summary), requestId=request.state.request_id)
