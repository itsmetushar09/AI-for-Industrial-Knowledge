"""Database-backed operational and AI analytics."""

from datetime import UTC, date, datetime, timedelta
from typing import Annotated

from fastapi import Depends
from sqlalchemy import BigInteger, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db_session
from app.models.audit import AuditLog
from app.models.department import Department
from app.models.document import Document
from app.schemas.analytics import (
    AiUsagePoint,
    AnalyticsResponse,
    DepartmentAnalytics,
    UploadTrendPoint,
)

ANALYTICS_DAYS = 30


class AnalyticsService:
    """Aggregate dashboard metrics without retaining a separate analytics store."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def snapshot(self, today: date | None = None) -> AnalyticsResponse:
        """Return current totals and zero-filled 30-day UTC trends."""

        end_date = today or datetime.now(UTC).date()
        start_date = end_date - timedelta(days=ANALYTICS_DAYS - 1)
        start_time = datetime.combine(start_date, datetime.min.time(), tzinfo=UTC)
        end_time = datetime.combine(end_date + timedelta(days=1), datetime.min.time(), tzinfo=UTC)

        total_documents = int(await self.session.scalar(select(func.count(Document.id))) or 0)
        storage_usage_bytes = int(
            await self.session.scalar(select(func.coalesce(func.sum(Document.size_bytes), 0))) or 0
        )
        total_uploads = int(
            await self.session.scalar(
                select(func.count(AuditLog.id)).where(AuditLog.action == "document.uploaded")
            )
            or 0
        )
        total_ai_questions = int(
            await self.session.scalar(
                select(func.count(AuditLog.id)).where(AuditLog.action == "ai.question_asked")
            )
            or 0
        )

        top_department_rows = (
            await self.session.execute(
                select(
                    Department.id,
                    Department.name,
                    func.count(Document.id).label("documents"),
                    func.coalesce(func.sum(Document.size_bytes), 0).label("storage_bytes"),
                )
                .join(Document, Document.department_id == Department.id)
                .group_by(Department.id, Department.name)
                .order_by(func.count(Document.id).desc(), Department.name.asc())
                .limit(5)
            )
        ).all()

        upload_day = func.date(AuditLog.created_at).label("day")
        uploaded_bytes = AuditLog.details["size_bytes"].astext.cast(BigInteger)
        upload_rows = (
            await self.session.execute(
                select(
                    upload_day,
                    func.count(AuditLog.id),
                    func.coalesce(func.sum(uploaded_bytes), 0),
                )
                .where(
                    AuditLog.action == "document.uploaded",
                    AuditLog.created_at >= start_time,
                    AuditLog.created_at < end_time,
                )
                .group_by(upload_day)
                .order_by(upload_day)
            )
        ).all()

        ai_day = func.date(AuditLog.created_at).label("day")
        ai_rows = (
            await self.session.execute(
                select(ai_day, func.count(AuditLog.id))
                .where(
                    AuditLog.action == "ai.question_asked",
                    AuditLog.created_at >= start_time,
                    AuditLog.created_at < end_time,
                )
                .group_by(ai_day)
                .order_by(ai_day)
            )
        ).all()

        upload_by_day = {
            self._date_value(day): (int(uploads), int(byte_count))
            for day, uploads, byte_count in upload_rows
        }
        ai_by_day = {self._date_value(day): int(questions) for day, questions in ai_rows}
        days = [start_date + timedelta(days=offset) for offset in range(ANALYTICS_DAYS)]

        return AnalyticsResponse(
            total_documents=total_documents,
            total_uploads=total_uploads,
            total_ai_questions=total_ai_questions,
            storage_usage_bytes=storage_usage_bytes,
            top_departments=[
                DepartmentAnalytics(
                    department_id=department_id,
                    department=name,
                    documents=int(documents),
                    storage_bytes=int(department_storage),
                )
                for department_id, name, documents, department_storage in top_department_rows
            ],
            upload_trends=[
                UploadTrendPoint(
                    date=day,
                    uploads=upload_by_day.get(day, (0, 0))[0],
                    bytes=upload_by_day.get(day, (0, 0))[1],
                )
                for day in days
            ],
            ai_usage=[
                AiUsagePoint(date=day, questions=ai_by_day.get(day, 0)) for day in days
            ],
        )

    @staticmethod
    def _date_value(value: date | datetime) -> date:
        return value.date() if isinstance(value, datetime) else value


def get_analytics_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AnalyticsService:
    """Inject request-scoped analytics aggregation."""

    return AnalyticsService(session)
