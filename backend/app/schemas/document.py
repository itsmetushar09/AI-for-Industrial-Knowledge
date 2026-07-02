"""Document upload, management, and semantic-search API schemas."""

import uuid
from datetime import datetime

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import DocumentStatus


class DocumentUploadResponse(BaseModel):
    """Metadata returned after a document has been durably queued."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    mime_type: str
    size_bytes: int
    status: DocumentStatus
    department_id: uuid.UUID | None
    created_at: datetime
    queued: bool = True


class DocumentSummary(BaseModel):
    """Safe document metadata returned by list operations."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    mime_type: str
    size_bytes: int
    status: DocumentStatus
    department_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
    processed_at: datetime | None


class DocumentListResponse(BaseModel):
    """Paginated document collection."""

    items: list[DocumentSummary]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)


class DocumentDetail(DocumentSummary):
    """Document metadata plus processing diagnostics and chunk statistics."""

    error_message: str | None
    metadata: dict[str, Any]
    chunk_count: int = Field(ge=0)
    page_count: int = Field(ge=0)


class DocumentSearchHit(BaseModel):
    """One semantically similar document passage."""

    document_id: uuid.UUID
    document: str
    page: int = Field(ge=1)
    content: str
    score: float = Field(ge=0, le=1)
