"""Authenticated profile and read-only frontend adapter tests."""

import uuid
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.database.session import get_database, get_db_session
from app.main import app
from app.models.enums import UserRole


class ScalarRows:
    def __init__(self, rows: list[object]) -> None:
        self.rows = rows

    def all(self) -> list[object]:
        return self.rows


def test_compliance_returns_real_empty_state() -> None:
    with TestClient(app) as client:
        response = client.get("/compliance")

    assert response.status_code == 200
    assert response.json() == []


def test_graph_serializes_persisted_nodes_and_edges() -> None:
    node_a = uuid.uuid4()
    node_b = uuid.uuid4()

    class GraphSession:
        calls = 0

        async def scalars(self, _: object) -> ScalarRows:
            self.calls += 1
            if self.calls == 1:
                return ScalarRows(
                    [
                        SimpleNamespace(id=node_a, label="Pump A", node_type="Machine"),
                        SimpleNamespace(id=node_b, label="Maintenance", node_type="Department"),
                    ]
                )
            return ScalarRows(
                [
                    SimpleNamespace(
                        source_node_id=node_a,
                        target_node_id=node_b,
                        relation_type="Owned By",
                    )
                ]
            )

    app.dependency_overrides[get_db_session] = lambda: GraphSession()
    try:
        with TestClient(app) as client:
            response = client.get("/graph")
    finally:
        app.dependency_overrides.pop(get_db_session, None)

    assert response.status_code == 200
    assert response.json()["edges"] == [
        {"from": str(node_a), "to": str(node_b), "label": "Owned By"}
    ]


def test_current_user_returns_authoritative_profile(authenticated_api_user) -> None:
    user = authenticated_api_user
    profile = SimpleNamespace(id=user.id, full_name="Production Admin")

    class ProfileSession:
        async def __aenter__(self) -> "ProfileSession":
            return self

        async def __aexit__(self, *_: object) -> None:
            return None

        async def get(self, *_: object) -> object:
            return profile

    database = SimpleNamespace(session_factory=lambda: ProfileSession())
    app.dependency_overrides[get_database] = lambda: database
    try:
        with TestClient(app) as client:
            response = client.get("/auth/me")
    finally:
        app.dependency_overrides.pop(get_database, None)

    assert response.status_code == 200
    assert response.json() == {
        "id": str(user.id),
        "name": "Production Admin",
        "email": "admin@example.com",
        "role": UserRole.ADMINISTRATOR.value,
        "department_id": None,
    }
