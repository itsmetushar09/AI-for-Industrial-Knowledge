"""Run a self-cleaning Phase 4 upload against configured Supabase services."""

import asyncio
import json
import uuid

from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.core.supabase import get_supabase_clients
from app.database.session import get_database
from app.main import app
from app.models.audit import AuditLog
from app.models.document import Document
from app.storage.service import SupabaseStorageService

SMOKE_PDF = b"%PDF-1.4\n% INDUS AI Phase 4 smoke test\n%%EOF\n"


async def verify_and_cleanup(document_id: uuid.UUID) -> dict[str, object]:
    """Verify database and object bytes, then remove the generated test data."""

    database = get_database()
    clients = get_supabase_clients()
    if database.session_factory is None:
        raise RuntimeError("DATABASE_URL must be configured")

    storage = SupabaseStorageService(clients, clients.settings)
    storage_verified = False
    database_verified = False
    storage_path: str | None = None
    try:
        async with database.session_factory() as session:
            document = await session.scalar(select(Document).where(Document.id == document_id))
            if document is None:
                raise RuntimeError("Uploaded document metadata was not found")
            database_verified = document.status.value == "queued"
            storage_path = document.storage_path

        downloaded = await storage.download(storage_path)
        storage_verified = downloaded == SMOKE_PDF
        if not storage_verified:
            raise RuntimeError("Stored object content did not match the upload")

        await storage.delete(storage_path)
        async with database.session_factory() as session:
            await session.execute(
                delete(AuditLog).where(
                    AuditLog.entity_type == "document", AuditLog.entity_id == document_id
                )
            )
            await session.execute(delete(Document).where(Document.id == document_id))
            await session.commit()
    finally:
        await clients.close()
        await database.dispose()
        get_supabase_clients.cache_clear()
        get_database.cache_clear()

    return {
        "status": "passed",
        "http": 202,
        "database_verified": database_verified,
        "storage_verified": storage_verified,
        "cleanup": True,
    }


def main() -> None:
    """Upload through FastAPI, validate integrations, and report sanitized results."""

    with TestClient(app) as client:
        response = client.post(
            "/upload",
            files={"file": ("phase-4-smoke.pdf", SMOKE_PDF, "application/pdf")},
        )
    if response.status_code != 202:
        raise SystemExit(f"Upload smoke test failed with HTTP {response.status_code}")

    document_id = uuid.UUID(response.json()["id"])
    result = asyncio.run(verify_and_cleanup(document_id))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

