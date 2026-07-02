"""Validated PDF ingestion into private storage and PostgreSQL."""

import logging
import re
import time
import uuid
from pathlib import PurePath
from typing import Annotated

from fastapi import Depends, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.database.session import get_db_session
from app.models.audit import AuditLog
from app.models.department import Department
from app.models.document import Document
from app.models.enums import DocumentStatus
from app.storage.service import SupabaseStorageService, get_storage_service

READ_CHUNK_SIZE = 1024 * 1024
ACCEPTED_PDF_CONTENT_TYPES = {
    "application/pdf",
    "application/x-pdf",
    "application/octet-stream",
}
logger = logging.getLogger(__name__)


class UploadError(Exception):
    """Expected upload failure with an HTTP-safe message and status."""

    def __init__(self, message: str, status_code: int) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class DocumentUploadService:
    """Coordinate validation, object storage, metadata, and compensation."""

    def __init__(
        self,
        session: AsyncSession,
        storage: SupabaseStorageService,
        settings: Settings,
    ) -> None:
        self.session = session
        self.storage = storage
        self.settings = settings

    async def upload(
        self,
        file: UploadFile,
        department_id: uuid.UUID | None,
        user_id: uuid.UUID,
    ) -> Document:
        """Validate and persist one PDF, returning its queued database record."""

        started = time.perf_counter()

        try:
            filename = self._safe_filename(file.filename)
            content = await self._read_validated_pdf(file)
        finally:
            await file.close()

        if department_id is not None:
            department = await self.session.get(Department, department_id)
            if department is None:
                raise UploadError("Department not found", status.HTTP_404_NOT_FOUND)

        document_id = uuid.uuid4()
        storage_path = f"{document_id}/{filename}"
        try:
            await self.storage.upload(storage_path, content, "application/pdf")
        except Exception as exc:
            raise UploadError(
                "Document storage is temporarily unavailable",
                status.HTTP_502_BAD_GATEWAY,
            ) from exc

        document = Document(
            id=document_id,
            name=filename,
            storage_path=storage_path,
            mime_type="application/pdf",
            size_bytes=len(content),
            status=DocumentStatus.QUEUED,
            department_id=department_id,
            uploaded_by=user_id,
            metadata_={"original_filename": file.filename or filename},
        )
        self.session.add(document)
        self.session.add(
            AuditLog(
                actor_id=user_id,
                action="document.uploaded",
                entity_type="document",
                entity_id=document_id,
                details={"filename": filename, "size_bytes": len(content)},
            )
        )

        try:
            await self.session.flush()
            await self.session.refresh(document)
            await self.session.commit()
        except Exception as exc:
            await self.session.rollback()
            try:
                await self.storage.delete(storage_path)
            except Exception:
                logger.exception(
                    "Failed to remove orphaned upload",
                    extra={"event": "upload_compensation_failed", "storage_path": storage_path},
                )
            raise UploadError(
                "Unable to save document metadata",
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            ) from exc
        logger.info(
            "Document upload accepted",
            extra={
                "event": "document_uploaded",
                "document_id": str(document.id),
                "user_id": str(user_id),
                "department_id": str(department_id) if department_id else None,
                "size_bytes": document.size_bytes,
                "duration_ms": round((time.perf_counter() - started) * 1000, 2),
            },
        )
        return document

    async def _read_validated_pdf(self, file: UploadFile) -> bytes:
        """Read with a hard size cap and verify MIME type and PDF signature."""

        content_type = (file.content_type or "").lower()
        if content_type not in ACCEPTED_PDF_CONTENT_TYPES:
            raise UploadError("Only PDF documents are supported", status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

        content = bytearray()
        maximum = self.settings.supabase_storage_max_file_size
        while chunk := await file.read(READ_CHUNK_SIZE):
            content.extend(chunk)
            if len(content) > maximum:
                raise UploadError(
                    f"Document exceeds the {maximum // (1024 * 1024)} MiB upload limit",
                    status.HTTP_413_CONTENT_TOO_LARGE,
                )

        if not content:
            raise UploadError("The uploaded document is empty", status.HTTP_400_BAD_REQUEST)
        if not bytes(content[:1024]).lstrip().startswith(b"%PDF-"):
            raise UploadError("The uploaded file is not a valid PDF", status.HTTP_422_UNPROCESSABLE_CONTENT)
        return bytes(content)

    @staticmethod
    def _safe_filename(filename: str | None) -> str:
        """Remove path traversal and unsafe storage-path characters."""

        if not filename:
            raise UploadError("A filename is required", status.HTTP_400_BAD_REQUEST)
        basename = PurePath(filename.replace("\\", "/")).name.strip()
        if not basename.lower().endswith(".pdf"):
            raise UploadError("The filename must end with .pdf", status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)
        sanitized = re.sub(r"[^\w.() -]", "_", basename, flags=re.UNICODE)
        stem = sanitized[:-4].strip(" .")[:240]
        if not stem:
            raise UploadError("The filename is invalid", status.HTTP_400_BAD_REQUEST)
        return f"{stem}.pdf"


def get_document_upload_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    storage: Annotated[SupabaseStorageService, Depends(get_storage_service)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> DocumentUploadService:
    """Inject the upload orchestration service."""

    return DocumentUploadService(session, storage, settings)
