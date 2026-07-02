"""Phase 3 schema contract tests."""

from importlib import import_module

from pgvector.sqlalchemy import VECTOR

from app.models import Base

migration = import_module("migrations.versions.202607010001_phase3_initial_schema")

EXPECTED_TABLES = {
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
}


def test_all_phase_three_tables_are_mapped() -> None:
    application_tables = {
        table.name for table in Base.metadata.tables.values() if not table.info.get("external")
    }
    assert application_tables == EXPECTED_TABLES


def test_profile_is_linked_to_supabase_auth_user() -> None:
    profile_id = Base.metadata.tables["profiles"].c.id
    targets = {foreign_key.target_fullname for foreign_key in profile_id.foreign_keys}
    assert targets == {"auth.users.id"}


def test_document_embedding_dimension() -> None:
    embedding_type = Base.metadata.tables["document_chunks"].c.embedding.type
    assert isinstance(embedding_type, VECTOR)
    assert embedding_type.dim == 1536
    chunks = Base.metadata.tables["document_chunks"]
    assert "embedding_provider" in chunks.c
    assert "embedding_model" in chunks.c


def test_migration_secures_every_application_table() -> None:
    assert set(migration.TABLES_WITH_RLS) == EXPECTED_TABLES
