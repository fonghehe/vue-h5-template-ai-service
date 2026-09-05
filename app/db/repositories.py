"""Ownership-aware repositories; routes never query cross-user rows directly."""

from __future__ import annotations

import builtins
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import CODE_FORBIDDEN, CODE_NOT_FOUND, AppError
from app.db.models import Conversation, Document, DocumentChunk, Message, UsageRecord


class ConversationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, *, user_id: str, title: str, model: str) -> Conversation:
        conversation = Conversation(user_id=user_id, title=title, model=model)
        self.session.add(conversation)
        await self.session.commit()
        await self.session.refresh(conversation)
        return conversation

    async def list(self, user_id: str) -> builtins.list[Conversation]:
        rows = await self.session.scalars(
            select(Conversation).where(Conversation.user_id == user_id).order_by(Conversation.updated_at.desc())
        )
        return builtins.list(rows)

    async def get_owned(self, conversation_id: str, user_id: str, *, messages: bool = False) -> Conversation:
        statement = select(Conversation).where(Conversation.id == conversation_id)
        if messages:
            statement = statement.options(selectinload(Conversation.messages)).execution_options(populate_existing=True)
        conversation = await self.session.scalar(statement)
        if conversation is None:
            raise AppError("Conversation not found", code=CODE_NOT_FOUND, status_code=404)
        if conversation.user_id != user_id:
            raise AppError("Conversation access denied", code=CODE_FORBIDDEN, status_code=403)
        if messages:
            conversation.messages.sort(key=lambda message: message.sequence)
        return conversation

    async def delete_owned(self, conversation_id: str, user_id: str) -> None:
        conversation = await self.get_owned(conversation_id, user_id)
        await self.session.delete(conversation)
        await self.session.commit()

    async def add_message(
        self,
        conversation: Conversation,
        *,
        role: str,
        content: str,
        tool_call_id: str | None = None,
        token_usage: dict[str, Any] | None = None,
        latency_ms: float | None = None,
        citations: builtins.list[dict[str, Any]] | None = None,
    ) -> Message:
        sequence = (
            int(
                await self.session.scalar(
                    select(func.coalesce(func.max(Message.sequence), 0)).where(
                        Message.conversation_id == conversation.id
                    )
                )
                or 0
            )
            + 1
        )
        message = Message(
            conversation_id=conversation.id,
            sequence=sequence,
            role=role,
            content=content,
            tool_call_id=tool_call_id,
            token_usage=token_usage,
            latency_ms=latency_ms,
            citations=citations,
        )
        conversation.updated_at = datetime.now(UTC)
        self.session.add(message)
        await self.session.commit()
        await self.session.refresh(message)
        return message


class UsageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, record: UsageRecord) -> None:
        self.session.add(record)
        await self.session.commit()

    async def summary(self, user_id: str, usage_date: date | None = None) -> dict[str, Any]:
        statement = select(
            func.coalesce(func.sum(UsageRecord.prompt_tokens), 0),
            func.coalesce(func.sum(UsageRecord.completion_tokens), 0),
            func.coalesce(func.sum(UsageRecord.total_tokens), 0),
            func.count(UsageRecord.id),
        ).where(UsageRecord.user_id == user_id)
        if usage_date is not None:
            statement = statement.where(UsageRecord.usage_date == usage_date)
        row = (await self.session.execute(statement)).one()
        summary: dict[str, Any] = {
            "promptTokens": int(row[0]),
            "completionTokens": int(row[1]),
            "totalTokens": int(row[2]),
            "requests": int(row[3]),
        }
        if usage_date is None:
            summary["byModel"] = await self._breakdown(user_id, UsageRecord.model)
            summary["byConversation"] = await self._breakdown(user_id, UsageRecord.conversation_id)
            summary["byDate"] = await self._breakdown(user_id, UsageRecord.usage_date)
        return summary

    async def _breakdown(self, user_id: str, group_column: Any) -> builtins.list[dict[str, Any]]:
        rows = await self.session.execute(
            select(
                group_column,
                func.coalesce(func.sum(UsageRecord.prompt_tokens), 0),
                func.coalesce(func.sum(UsageRecord.completion_tokens), 0),
                func.coalesce(func.sum(UsageRecord.total_tokens), 0),
                func.count(UsageRecord.id),
            )
            .where(UsageRecord.user_id == user_id)
            .group_by(group_column)
            .order_by(group_column)
        )
        return [
            {
                "key": str(row[0] or "unknown"),
                "promptTokens": int(row[1]),
                "completionTokens": int(row[2]),
                "totalTokens": int(row[3]),
                "requests": int(row[4]),
            }
            for row in rows
        ]


class KnowledgeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, document: Document, chunks: list[DocumentChunk]) -> Document:
        document.chunks = chunks
        self.session.add(document)
        await self.session.commit()
        await self.session.refresh(document)
        return document

    async def list(self, user_id: str) -> builtins.list[Document]:
        rows = await self.session.scalars(
            select(Document).where(Document.user_id == user_id).order_by(Document.created_at.desc())
        )
        return builtins.list(rows)

    async def delete_owned(self, document_id: str, user_id: str) -> None:
        document = await self.session.scalar(select(Document).where(Document.id == document_id))
        if document is None:
            raise AppError("Document not found", code=CODE_NOT_FOUND, status_code=404)
        if document.user_id != user_id:
            raise AppError("Document access denied", code=CODE_FORBIDDEN, status_code=403)
        await self.session.execute(delete(Document).where(Document.id == document_id))
        await self.session.commit()

    async def chunks(self, user_id: str) -> builtins.list[tuple[DocumentChunk, Document]]:
        rows = await self.session.execute(
            select(DocumentChunk, Document)
            .join(Document, Document.id == DocumentChunk.document_id)
            .where(Document.user_id == user_id)
        )
        return [(chunk, document) for chunk, document in rows]

    async def search_similar(
        self, user_id: str, vector: builtins.list[float], top_k: int
    ) -> builtins.list[tuple[DocumentChunk, Document, float]] | None:
        bind = self.session.get_bind()
        if bind.dialect.name != "postgresql":
            return None
        distance = DocumentChunk.embedding.cosine_distance(vector)
        rows = await self.session.execute(
            select(DocumentChunk, Document, distance.label("distance"))
            .join(Document, Document.id == DocumentChunk.document_id)
            .where(Document.user_id == user_id)
            .order_by(distance)
            .limit(top_k)
        )
        return [(chunk, document, 1.0 - float(value)) for chunk, document, value in rows]
