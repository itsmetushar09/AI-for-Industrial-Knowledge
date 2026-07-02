"""Track the embedding space used by each document chunk.

Revision ID: 202607010002
Revises: 202607010001
Create Date: 2026-07-01
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "202607010002"
down_revision: str | None = "202607010001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Tag existing OpenAI vectors and support provider-safe retrieval."""

    op.add_column(
        "document_chunks",
        sa.Column("embedding_provider", sa.String(length=32), nullable=True),
        schema="public",
    )
    op.add_column(
        "document_chunks",
        sa.Column("embedding_model", sa.String(length=120), nullable=True),
        schema="public",
    )
    op.execute(
        "UPDATE public.document_chunks "
        "SET embedding_provider = 'openai', embedding_model = 'text-embedding-3-small' "
        "WHERE embedding IS NOT NULL"
    )
    op.create_index(
        "ix_document_chunks_embedding_space",
        "document_chunks",
        ["embedding_provider", "embedding_model"],
        schema="public",
    )


def downgrade() -> None:
    """Remove embedding-space metadata without touching stored vectors."""

    op.drop_index(
        "ix_document_chunks_embedding_space",
        table_name="document_chunks",
        schema="public",
    )
    op.drop_column("document_chunks", "embedding_model", schema="public")
    op.drop_column("document_chunks", "embedding_provider", schema="public")

