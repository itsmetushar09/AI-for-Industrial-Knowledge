"""Document metadata, deletion, and semantic-search endpoints."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.core.auth import AuthenticatedUser, get_current_user, require_roles
from app.models.enums import DocumentStatus
from app.models.enums import UserRole
from app.schemas.document import (
    DocumentDetail,
    DocumentListResponse,
    DocumentSearchHit,
)
from app.services.documents import DocumentService, DocumentServiceError, get_document_service

router = APIRouter(prefix="/documents", tags=["documents"])


def raise_document_error(exc: DocumentServiceError) -> None:
    """Translate an expected application error to the HTTP boundary."""

    raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.get("", response_model=DocumentListResponse, summary="List documents")
async def list_documents(
    service: Annotated[DocumentService, Depends(get_document_service)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
    document_status: Annotated[DocumentStatus | None, Query(alias="status")] = None,
    department_id: uuid.UUID | None = None,
) -> DocumentListResponse:
    """List newest documents with optional status and department filters."""

    return await service.list_documents(page, page_size, document_status, department_id)


@router.get("/search", response_model=list[DocumentSearchHit], summary="Semantic document search")
async def search_documents(
    service: Annotated[DocumentService, Depends(get_document_service)],
    query: Annotated[str, Query(alias="q", min_length=2, max_length=4000)],
    limit: Annotated[int, Query(ge=1, le=20)] = 10,
    department_id: uuid.UUID | None = None,
) -> list[DocumentSearchHit]:
    """Search indexed chunks exclusively by vector similarity."""

    query = query.strip()
    if len(query) < 2:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Search query must contain at least two characters",
        )
    try:
        return await service.semantic_search(query, limit, department_id)
    except DocumentServiceError as exc:
        raise_document_error(exc)


@router.get("/{document_id}", response_model=DocumentDetail, summary="Get document details")
async def get_document(
    document_id: uuid.UUID,
    service: Annotated[DocumentService, Depends(get_document_service)],
) -> DocumentDetail:
    """Return one document with processing and indexing details."""

    try:
        return await service.detail(document_id)
    except DocumentServiceError as exc:
        raise_document_error(exc)


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[
        Depends(require_roles(UserRole.ADMINISTRATOR, UserRole.PLANT_MANAGER))
    ],
)
async def delete_document(
    document_id: uuid.UUID,
    service: Annotated[DocumentService, Depends(get_document_service)],
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> Response:
    """Delete a document, its private object, and cascade-owned chunks."""

    try:
        await service.delete(document_id, user.id)
    except DocumentServiceError as exc:
        raise_document_error(exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
