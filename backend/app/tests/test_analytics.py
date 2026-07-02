"""Phase 9 analytics API tests."""

import uuid
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.analytics import (
    AiUsagePoint,
    AnalyticsResponse,
    DepartmentAnalytics,
    UploadTrendPoint,
)
from app.services.analytics import ANALYTICS_DAYS, AnalyticsService, get_analytics_service


class FakeAnalyticsService:
    async def snapshot(self) -> AnalyticsResponse:
        today = date(2026, 7, 2)
        return AnalyticsResponse(
            total_documents=2,
            total_uploads=3,
            total_ai_questions=4,
            storage_usage_bytes=4096,
            top_departments=[
                DepartmentAnalytics(
                    department_id=uuid.UUID("3fa85f64-5717-4562-b3fc-2c963f66afa6"),
                    department="Maintenance",
                    documents=2,
                    storage_bytes=4096,
                )
            ],
            upload_trends=[UploadTrendPoint(date=today, uploads=1, bytes=2048)],
            ai_usage=[AiUsagePoint(date=today, questions=2)],
        )


def test_analytics_endpoint_contract() -> None:
    app.dependency_overrides[get_analytics_service] = lambda: FakeAnalyticsService()
    try:
        with TestClient(app) as client:
            response = client.get("/analytics")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_documents"] == 2
    assert payload["total_uploads"] == 3
    assert payload["total_ai_questions"] == 4
    assert payload["storage_usage_bytes"] == 4096
    assert payload["top_departments"][0]["department"] == "Maintenance"
    assert payload["upload_trends"][0]["date"] == "2026-07-02"
    assert payload["ai_usage"][0]["questions"] == 2


def test_analytics_window_is_thirty_days() -> None:
    assert ANALYTICS_DAYS == 30
    end = date(2026, 7, 2)
    start = end - timedelta(days=ANALYTICS_DAYS - 1)
    assert (end - start).days == 29


def test_date_value_accepts_database_date() -> None:
    value = date(2026, 7, 2)
    assert AnalyticsService._date_value(value) == value


class FakeRows:
    def __init__(self, rows: list[tuple[object, ...]]) -> None:
        self.rows = rows

    def all(self) -> list[tuple[object, ...]]:
        return self.rows


class AggregationSession:
    def __init__(self, department_id: uuid.UUID) -> None:
        self.scalars = [2, 4096, 3, 4]
        self.results = [
            [(department_id, "Maintenance", 2, 4096)],
            [(date(2026, 7, 1), 2, 3072)],
            [(date(2026, 7, 2), 3)],
        ]

    async def scalar(self, _: object) -> int:
        return self.scalars.pop(0)

    async def execute(self, _: object) -> FakeRows:
        return FakeRows(self.results.pop(0))


@pytest.mark.asyncio
async def test_analytics_aggregates_and_zero_fills_thirty_days() -> None:
    department_id = uuid.uuid4()
    service = AnalyticsService(AggregationSession(department_id))  # type: ignore[arg-type]

    result = await service.snapshot(today=date(2026, 7, 2))

    assert result.total_documents == 2
    assert result.total_uploads == 3
    assert result.total_ai_questions == 4
    assert result.storage_usage_bytes == 4096
    assert result.top_departments[0].department_id == department_id
    assert len(result.upload_trends) == 30
    assert result.upload_trends[-2].uploads == 2
    assert result.upload_trends[-2].bytes == 3072
    assert result.upload_trends[-1].uploads == 0
    assert result.ai_usage[-1].questions == 3
