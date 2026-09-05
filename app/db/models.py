"""SQLAlchemy models for conversations, knowledge, and usage."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any
from uuid import uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, Date, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _uuid() -> str:
    return str(uuid4())


def _now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (Index("ix_conversations_user_updated", "user_id", "updated_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(120), index=True)
    title: Mapped[str] = mapped_column(String(200), default="New conversation")
    model: Mapped[str] = mapped_column(String(120))
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)
    messages: Mapped[list[Message]] = relationship(back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (UniqueConstraint("conversation_id", "sequence", name="uq_messages_conversation_sequence"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), index=True)
    sequence: Mapped[int] = mapped_column(Integer)
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    tool_call_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    token_usage: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    citations: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    conversation: Mapped[Conversation] = relationship(back_populates="messages")


class UsageRecord(Base):
    __tablename__ = "usage_records"
    __table_args__ = (Index("ix_usage_user_date", "user_id", "usage_date"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(120), index=True)
    conversation_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    model: Mapped[str] = mapped_column(String(120))
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[float] = mapped_column(Float, default=0)
    usage_date: Mapped[date] = mapped_column(Date, default=lambda: datetime.now(UTC).date())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (Index("ix_documents_user_created", "user_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(120), index=True)
    title: Mapped[str] = mapped_column(String(240))
    source: Mapped[str] = mapped_column(String(500))
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    chunks: Mapped[list[DocumentChunk]] = relationship(back_populates="document", cascade="all, delete-orphan")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    __table_args__ = (UniqueConstraint("document_id", "chunk_index", name="uq_document_chunks_index"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    chunk_index: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    # PostgreSQL gets pgvector; SQLite stores the same list as JSON for offline tests.
    embedding: Mapped[list[float]] = mapped_column(Vector().with_variant(JSON, "sqlite"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    document: Mapped[Document] = relationship(back_populates="chunks")
