"""Create the Phase 3 industrial knowledge schema.

Revision ID: 202607010001
Revises: None
Create Date: 2026-07-01
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import VECTOR
from sqlalchemy.dialects import postgresql

revision: str = "202607010001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

user_role = postgresql.ENUM(
    "administrator",
    "plant_manager",
    "maintenance_engineer",
    "safety_officer",
    "operator",
    name="user_role",
    create_type=False,
)
document_status = postgresql.ENUM(
    "queued", "processing", "indexed", "failed", name="document_status", create_type=False
)
message_role = postgresql.ENUM(
    "user", "assistant", "system", name="message_role", create_type=False
)
equipment_status = postgresql.ENUM(
    "operational",
    "maintenance",
    "out_of_service",
    "decommissioned",
    name="equipment_status",
    create_type=False,
)

TABLES_WITH_RLS = (
    "departments",
    "profiles",
    "documents",
    "document_chunks",
    "conversations",
    "messages",
    "knowledge_nodes",
    "knowledge_edges",
    "equipment",
    "audit_logs",
)
TABLES_WITH_UPDATED_AT = ("departments", "profiles", "documents", "conversations", "equipment")


def upgrade() -> None:
    """Create application types, tables, indexes, triggers, and RLS boundaries."""

    bind = op.get_bind()
    op.execute("CREATE SCHEMA IF NOT EXISTS extensions")
    op.execute("CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA extensions")
    user_role.create(bind, checkfirst=True)
    document_status.create(bind, checkfirst=True)
    message_role.create(bind, checkfirst=True)
    equipment_status.create(bind, checkfirst=True)

    op.create_table(
        "departments",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_departments"),
        sa.UniqueConstraint("code", name="uq_departments_code"),
        sa.UniqueConstraint("name", name="uq_departments_name"),
        schema="public",
    )
    op.create_table(
        "profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("full_name", sa.String(length=160), nullable=False),
        sa.Column("role", user_role, server_default=sa.text("'operator'::user_role"), nullable=False),
        sa.Column("department_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("job_title", sa.String(length=120), nullable=True),
        sa.Column("avatar_url", sa.String(length=2048), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["department_id"], ["public.departments.id"], name="fk_profiles_department_id_departments", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["id"], ["auth.users.id"], name="fk_profiles_id_users", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_profiles"),
        schema="public",
    )
    op.create_index("ix_profiles_department_id", "profiles", ["department_id"], schema="public")

    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("name", sa.String(length=512), nullable=False),
        sa.Column("storage_path", sa.String(length=1024), nullable=False),
        sa.Column("mime_type", sa.String(length=128), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("status", document_status, server_default=sa.text("'queued'::document_status"), nullable=False),
        sa.Column("department_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("uploaded_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("size_bytes >= 0", name="size_nonnegative"),
        sa.ForeignKeyConstraint(["department_id"], ["public.departments.id"], name="fk_documents_department_id_departments", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["uploaded_by"], ["public.profiles.id"], name="fk_documents_uploaded_by_profiles", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_documents"),
        sa.UniqueConstraint("storage_path", name="uq_documents_storage_path"),
        schema="public",
    )
    op.create_index("ix_documents_department_id", "documents", ["department_id"], schema="public")
    op.create_index("ix_documents_uploaded_by", "documents", ["uploaded_by"], schema="public")
    op.create_index("ix_documents_department_status", "documents", ["department_id", "status"], schema="public")

    op.create_table(
        "document_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("embedding", VECTOR(dim=1536), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("chunk_index >= 0", name="index_nonnegative"),
        sa.CheckConstraint("token_count > 0", name="token_count_positive"),
        sa.CheckConstraint("page_number > 0", name="page_positive"),
        sa.ForeignKeyConstraint(["document_id"], ["public.documents.id"], name="fk_document_chunks_document_id_documents", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_document_chunks"),
        sa.UniqueConstraint("document_id", "chunk_index", name="uq_document_chunks_position"),
        schema="public",
    )
    op.create_index("ix_document_chunks_document_page", "document_chunks", ["document_id", "page_number"], schema="public")
    op.execute(
        "CREATE INDEX ix_document_chunks_embedding_hnsw ON public.document_chunks "
        "USING hnsw (embedding vector_cosine_ops)"
    )

    op.create_table(
        "conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["public.profiles.id"], name="fk_conversations_user_id_profiles", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_conversations"),
        schema="public",
    )
    op.create_index("ix_conversations_user_id", "conversations", ["user_id"], schema="public")
    op.create_table(
        "messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", message_role, nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("citations", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("confidence IS NULL OR (confidence >= 0 AND confidence <= 1)", name="confidence_range"),
        sa.ForeignKeyConstraint(["conversation_id"], ["public.conversations.id"], name="fk_messages_conversation_id_conversations", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_messages"),
        schema="public",
    )
    op.create_index("ix_messages_conversation_created", "messages", ["conversation_id", "created_at"], schema="public")

    op.create_table(
        "knowledge_nodes",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("label", sa.String(length=512), nullable=False),
        sa.Column("node_type", sa.String(length=80), nullable=False),
        sa.Column("properties", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("department_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_document_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["department_id"], ["public.departments.id"], name="fk_knowledge_nodes_department_id_departments", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_document_id"], ["public.documents.id"], name="fk_knowledge_nodes_source_document_id_documents", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_knowledge_nodes"),
        schema="public",
    )
    op.create_index("ix_knowledge_nodes_department_id", "knowledge_nodes", ["department_id"], schema="public")
    op.create_index("ix_knowledge_nodes_source_document_id", "knowledge_nodes", ["source_document_id"], schema="public")
    op.create_index("ix_knowledge_nodes_type_label", "knowledge_nodes", ["node_type", "label"], schema="public")
    op.create_table(
        "knowledge_edges",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("source_node_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_node_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("relation_type", sa.String(length=120), nullable=False),
        sa.Column("properties", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("source_node_id <> target_node_id", name="no_self_edge"),
        sa.ForeignKeyConstraint(["source_node_id"], ["public.knowledge_nodes.id"], name="fk_knowledge_edges_source_node_id_knowledge_nodes", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_node_id"], ["public.knowledge_nodes.id"], name="fk_knowledge_edges_target_node_id_knowledge_nodes", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_knowledge_edges"),
        sa.UniqueConstraint("source_node_id", "target_node_id", "relation_type", name="uq_knowledge_edge"),
        schema="public",
    )
    op.create_index("ix_knowledge_edges_source", "knowledge_edges", ["source_node_id"], schema="public")
    op.create_index("ix_knowledge_edges_target", "knowledge_edges", ["target_node_id"], schema="public")

    op.create_table(
        "equipment",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("name", sa.String(length=240), nullable=False),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("equipment_type", sa.String(length=120), nullable=False),
        sa.Column("department_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", equipment_status, server_default=sa.text("'operational'::equipment_status"), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["department_id"], ["public.departments.id"], name="fk_equipment_department_id_departments", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_equipment"),
        sa.UniqueConstraint("code", name="uq_equipment_code"),
        schema="public",
    )
    op.create_index("ix_equipment_department_id", "equipment", ["department_id"], schema="public")
    op.create_index("ix_equipment_department_status", "equipment", ["department_id", "status"], schema="public")

    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(length=160), nullable=False),
        sa.Column("entity_type", sa.String(length=120), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("ip_address", postgresql.INET(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["actor_id"], ["public.profiles.id"], name="fk_audit_logs_actor_id_profiles", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_audit_logs"),
        schema="public",
    )
    op.create_index("ix_audit_logs_actor_created", "audit_logs", ["actor_id", "created_at"], schema="public")
    op.create_index("ix_audit_logs_entity", "audit_logs", ["entity_type", "entity_id"], schema="public")

    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.set_updated_at()
        RETURNS trigger
        LANGUAGE plpgsql
        SET search_path = ''
        AS $$
        BEGIN
          NEW.updated_at = now();
          RETURN NEW;
        END;
        $$
        """
    )
    for table_name in TABLES_WITH_UPDATED_AT:
        op.execute(
            f"CREATE TRIGGER trg_{table_name}_updated_at BEFORE UPDATE ON public.{table_name} "
            "FOR EACH ROW EXECUTE FUNCTION public.set_updated_at()"
        )
    for table_name in TABLES_WITH_RLS:
        op.execute(f"ALTER TABLE public.{table_name} ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    """Remove only application-owned Phase 3 objects."""

    for table_name in TABLES_WITH_UPDATED_AT:
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table_name}_updated_at ON public.{table_name}")
    op.execute("DROP FUNCTION IF EXISTS public.set_updated_at()")

    for table_name in reversed(TABLES_WITH_RLS):
        op.drop_table(table_name, schema="public")

    bind = op.get_bind()
    equipment_status.drop(bind, checkfirst=True)
    message_role.drop(bind, checkfirst=True)
    document_status.drop(bind, checkfirst=True)
    user_role.drop(bind, checkfirst=True)
