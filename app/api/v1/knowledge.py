"""User-owned lightweight knowledge-base endpoints."""

from __future__ import annotations

import json
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ValidationError
from app.core.security import AuthenticatedUser, SettingsDep
from app.db.repositories import KnowledgeRepository
from app.db.session import get_db_session
from app.schemas.envelope import ApiResponse
from app.schemas.knowledge import DocumentView
from app.services.knowledge import KnowledgeService

router = APIRouter(prefix="/api/knowledge/documents", tags=["knowledge"])
DbSession = Annotated[AsyncSession, Depends(get_db_session)]


@router.post("", response_model=ApiResponse[DocumentView])
async def upload_document(
    request: Request,
    user: AuthenticatedUser,
    settings: SettingsDep,
    session: DbSession,
    file: Annotated[UploadFile, File()],
    metadata: Annotated[str, Form()] = "{}",
) -> ApiResponse[DocumentView]:
    data = await file.read(settings.knowledge_max_file_bytes + 1)
    if len(data) > settings.knowledge_max_file_bytes:
        raise ValidationError("File is too large")
    try:
        metadata_value: dict[str, Any] = json.loads(metadata)
        service = KnowledgeService(
            KnowledgeRepository(session),
            request.app.state.embedding_provider,
            chunk_chars=settings.knowledge_chunk_chars,
            overlap_chars=settings.knowledge_chunk_overlap_chars,
        )
        document = await service.ingest(
            user_id=user.subject,
            filename=file.filename or "document.txt",
            content_type=file.content_type,
            data=data,
            metadata=metadata_value,
        )
    except (ValueError, json.JSONDecodeError) as exc:
        raise ValidationError(str(exc)) from exc
    return ApiResponse(data=DocumentView.model_validate(document), requestId=request.state.request_id)


@router.get("", response_model=ApiResponse[list[DocumentView]])
async def list_documents(
    request: Request, user: AuthenticatedUser, session: DbSession
) -> ApiResponse[list[DocumentView]]:
    documents = await KnowledgeRepository(session).list(user.subject)
    return ApiResponse(
        data=[DocumentView.model_validate(item) for item in documents], requestId=request.state.request_id
    )


@router.delete("/{document_id}", response_model=ApiResponse[None])
async def delete_document(
    document_id: str, request: Request, user: AuthenticatedUser, session: DbSession
) -> ApiResponse[None]:
    await KnowledgeRepository(session).delete_owned(document_id, user.subject)
    return ApiResponse(data=None, requestId=request.state.request_id)
