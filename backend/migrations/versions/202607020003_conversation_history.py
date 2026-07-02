"""Support browser-scoped conversation history before authentication.

Revision ID: 202607020003
Revises: 202607010002
Create Date: 2026-07-02
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "202607020003"
down_revision: str | None = "202607010002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Permit either authenticated or anonymous ownership of a conversation."""

    op.alter_column("conversations", "user_id", nullable=True, schema="public")
    op.add_column(
        "conversations",
        sa.Column("anonymous_session_id", postgresql.UUID(as_uuid=True), nullable=True),
        schema="public",
    )
    op.create_index(
        "ix_conversations_anonymous_session_id",
        "conversations",
        ["anonymous_session_id"],
        schema="public",
    )
    op.create_check_constraint(
        "conversation_owner",
        "conversations",
        "num_nonnulls(user_id, anonymous_session_id) = 1",
        schema="public",
    )


def downgrade() -> None:
    """Restore authenticated-only ownership after removing anonymous rows."""

    op.drop_constraint(
        "ck_conversations_conversation_owner",
        "conversations",
        type_="check",
        schema="public",
    )
    op.drop_index(
        "ix_conversations_anonymous_session_id",
        table_name="conversations",
        schema="public",
    )
    op.drop_column("conversations", "anonymous_session_id", schema="public")
    op.alter_column("conversations", "user_id", nullable=False, schema="public")
