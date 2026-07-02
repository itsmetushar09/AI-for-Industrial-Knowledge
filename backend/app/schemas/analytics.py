"""Analytics API response contracts."""

import uuid
from datetime import date

from pydantic import BaseModel, Field


class DepartmentAnalytics(BaseModel):
    """Document and storage contribution for one department."""

    department_id: uuid.UUID
    department: str
    documents: int = Field(ge=0)
    storage_bytes: int = Field(ge=0)


class UploadTrendPoint(BaseModel):
    """One UTC day of upload activity."""

    date: date
    uploads: int = Field(ge=0)
    bytes: int = Field(ge=0)


class AiUsagePoint(BaseModel):
    """One UTC day of auditable AI questions."""

    date: date
    questions: int = Field(ge=0)


class AnalyticsResponse(BaseModel):
    """Dashboard-ready operational and AI usage analytics."""

    total_documents: int = Field(ge=0)
    total_uploads: int = Field(ge=0)
    total_ai_questions: int = Field(ge=0)
    storage_usage_bytes: int = Field(ge=0)
    top_departments: list[DepartmentAnalytics]
    upload_trends: list[UploadTrendPoint]
    ai_usage: list[AiUsagePoint]
