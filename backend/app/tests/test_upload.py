"""Phase 4 document upload tests."""

import uuid
from datetime import UTC, datetime
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from starlette.datastructures import Headers, UploadFile

from app.main import app
from app.models.document import Document
from app.models.enums import DocumentStatus
from app.services.document_upload import (
    DocumentUploadService,
    UploadError,
    get_document_upload_service,
)
from app.core.config import Settings


class UnusedSession:
    """Fail loudly if an invalid upload reaches persistence."""

    async def get(self, *_: object) -> object:
        raise AssertionError("database should not be accessed")


class UnusedStorage:
    async def upload(self, *_: object) -> None:
        raise AssertionError("storage should not be accessed")


class FailingStorage:
    def __init__(self, fail_upload: bool = False) -> None:
        self.fail_upload = fail_upload
        self.uploaded: list[str] = []
        self.deleted: list[str] = []

    async def upload(self, path: str, *_: object) -> None:
        if self.fail_upload:
            raise RuntimeError("storage unavailable")
        self.uploaded.append(path)

    async def delete(self, path: str) -> None:
        self.deleted.append(path)


class FlushFailingSession:
    def __init__(self) -> None:
        self.rollbacks = 0

    def add(self, _: object) -> None:
        return None

    async def flush(self) -> None:
        raise RuntimeError("database unavailable")

    async def rollback(self) -> None:
        self.rollbacks += 1


def upload_file(name: str, content: bytes, content_type: str) -> UploadFile:
    return UploadFile(
        BytesIO(content),
        filename=name,
        headers=Headers({"content-type": content_type}),
    )


@pytest.mark.asyncio
async def test_rejects_non_pdf_extension() -> None:
    user_id = uuid.uuid4()
    service = DocumentUploadService(
        UnusedSession(),  # type: ignore[arg-type]
        UnusedStorage(),  # type: ignore[arg-type]
        Settings(_env_file=None),
    )
    with pytest.raises(UploadError) as error:
        await service.upload(upload_file("manual.txt", b"hello", "text/plain"), None, user_id)
    assert error.value.status_code == 415


@pytest.mark.asyncio
async def test_rejects_spoofed_pdf() -> None:
    user_id = uuid.uuid4()
    service = DocumentUploadService(
        UnusedSession(),  # type: ignore[arg-type]
        UnusedStorage(),  # type: ignore[arg-type]
        Settings(_env_file=None),
    )
    with pytest.raises(UploadError) as error:
        await service.upload(upload_file("manual.pdf", b"not a pdf", "application/pdf"), None, user_id)
    assert error.value.status_code == 422


@pytest.mark.asyncio
async def test_enforces_configured_upload_limit() -> None:
    user_id = uuid.uuid4()
    service = DocumentUploadService(
        UnusedSession(),  # type: ignore[arg-type]
        UnusedStorage(),  # type: ignore[arg-type]
        Settings(supabase_storage_max_file_size=8, _env_file=None),
    )
    with pytest.raises(UploadError) as error:
        await service.upload(upload_file("manual.pdf", b"%PDF-1234", "application/pdf"), None, user_id)
    assert error.value.status_code == 413


def test_filename_is_sanitized_and_cannot_traverse() -> None:
    assert DocumentUploadService._safe_filename("../../Pump:A?.PDF") == "Pump_A_.pdf"


@pytest.mark.asyncio
async def test_storage_failure_does_not_create_metadata() -> None:
    storage = FailingStorage(fail_upload=True)
    service = DocumentUploadService(
        UnusedSession(),  # type: ignore[arg-type]
        storage,  # type: ignore[arg-type]
        Settings(_env_file=None),
    )

    with pytest.raises(UploadError) as error:
        await service.upload(
            upload_file("manual.pdf", b"%PDF-1.4 test", "application/pdf"),
            None,
            uuid.uuid4(),
        )

    assert error.value.status_code == 502
    assert storage.uploaded == []


@pytest.mark.asyncio
async def test_database_failure_removes_uploaded_object() -> None:
    session = FlushFailingSession()
    storage = FailingStorage()
    service = DocumentUploadService(
        session,  # type: ignore[arg-type]
        storage,  # type: ignore[arg-type]
        Settings(_env_file=None),
    )

    with pytest.raises(UploadError) as error:
        await service.upload(
            upload_file("manual.pdf", b"%PDF-1.4 test", "application/pdf"),
            None,
            uuid.uuid4(),
        )

    assert error.value.status_code == 500
    assert session.rollbacks == 1
    assert storage.deleted == storage.uploaded


def test_upload_endpoint_returns_accepted_document(monkeypatch: pytest.MonkeyPatch) -> None:
    document_id = uuid.uuid4()

    class FakeUploadService:
        async def upload(
            self,
            file: UploadFile,
            department_id: uuid.UUID | None,
            user_id: uuid.UUID,
        ) -> Document:
            assert file.filename == "manual.pdf"
            assert department_id is None
            assert user_id == uuid.UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
            return Document(
                id=document_id,
                name="manual.pdf",
                storage_path=f"{document_id}/manual.pdf",
                mime_type="application/pdf",
                size_bytes=14,
                status=DocumentStatus.QUEUED,
                department_id=None,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )

    app.dependency_overrides[get_document_upload_service] = lambda: FakeUploadService()
    async def no_processing(_: uuid.UUID) -> None:
        return None

    monkeypatch.setattr("app.api.upload.dispatch_document_processing", no_processing)
    try:
        with TestClient(app) as client:
            response = client.post(
                "/upload",
                files={"file": ("manual.pdf", b"%PDF-1.4 test", "application/pdf")},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 202
    payload = response.json()
    assert payload["id"] == str(document_id)
    assert payload["status"] == "queued"
    assert payload["queued"] is True
