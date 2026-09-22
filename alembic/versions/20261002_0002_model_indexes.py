"""Align indexes with SQLAlchemy metadata without modifying user records."""

from collections.abc import Sequence

from alembic import op

revision: str = "20261002_0002"
down_revision: str | None = "20260923_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_INDEXES = {
    "ix_conversations_user_id": ("conversations", "user_id"),
    "ix_usage_records_user_id": ("usage_records", "user_id"),
    "ix_usage_records_conversation_id": ("usage_records", "conversation_id"),
    "ix_documents_user_id": ("documents", "user_id"),
}


def upgrade() -> None:
    for name, (table, column) in _INDEXES.items():
        op.create_index(name, table, [column])


def downgrade() -> None:
    for name, (table, _) in reversed(_INDEXES.items()):
        op.drop_index(name, table_name=table)
