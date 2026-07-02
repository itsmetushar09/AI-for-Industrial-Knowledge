"""Document upload endpoint."""

import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, status

from app.core.auth import AuthenticatedUser, get_current_user, require_roles
from app.models.enums import UserRole
from app.schemas.document import DocumentUploadResponse
from app.services.document_upload import (
    DocumentUploadService,
    UploadError,
    get_document_upload_service,
)
from app.workers.document_processing import dispatch_document_processing

router = APIRouter(tags=["documents"])


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload and queue a PDF document",
    dependencies=[
        Depends(
            require_roles(
                UserRole.ADMINISTRATOR,
                UserRole.PLANT_MANAGER,
                UserRole.MAINTENANCE_ENGINEER,
                UserRole.SAFETY_OFFICER,
            )
        )
    ],
)
async def upload_document(
    background_tasks: BackgroundTasks,
    service: Annotated[DocumentUploadService, Depends(get_document_upload_service)],
    file: Annotated[UploadFile, File(description="Industrial PDF document")],
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    department_id: Annotated[uuid.UUID | None, Form()] = None,
) -> DocumentUploadResponse:
    """Store one validated PDF and durably queue it for processing."""

    try:
        document = await service.upload(file, department_id, user.id)
    except UploadError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    background_tasks.add_task(dispatch_document_processing, document.id)
    return DocumentUploadResponse.model_validate(document)
