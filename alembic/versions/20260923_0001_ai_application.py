"""AI application persistence and pgvector.

Revision ID: 20260923_0001
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "20260923_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "conversations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(120), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("model", sa.String(120), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_conversations_user_updated", "conversations", ["user_id", "updated_at"])
    op.create_table(
        "messages",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "conversation_id", sa.String(36), sa.ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("tool_call_id", sa.String(120), nullable=True),
        sa.Column("token_usage", sa.JSON(), nullable=True),
        sa.Column("latency_ms", sa.Float(), nullable=True),
        sa.Column("citations", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("conversation_id", "sequence", name="uq_messages_conversation_sequence"),
    )
    op.create_index("ix_messages_conversation_id", "messages", ["conversation_id"])
    op.create_table(
        "usage_records",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(120), nullable=False),
        sa.Column("conversation_id", sa.String(36), nullable=True),
        sa.Column("model", sa.String(120), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False),
        sa.Column("completion_tokens", sa.Integer(), nullable=False),
        sa.Column("total_tokens", sa.Integer(), nullable=False),
        sa.Column("latency_ms", sa.Float(), nullable=False),
        sa.Column("usage_date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_usage_user_date", "usage_records", ["user_id", "usage_date"])
    op.create_table(
        "documents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(120), nullable=False),
        sa.Column("title", sa.String(240), nullable=False),
        sa.Column("source", sa.String(500), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_documents_user_created", "documents", ["user_id", "created_at"])
    op.create_table(
        "document_chunks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("document_id", sa.String(36), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("document_id", "chunk_index", name="uq_document_chunks_index"),
    )
    op.create_index("ix_document_chunks_document_id", "document_chunks", ["document_id"])


def downgrade() -> None:
    for table in ("document_chunks", "documents", "usage_records", "messages", "conversations"):
        op.drop_table(table)
