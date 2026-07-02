"""Health endpoint contract tests."""

from fastapi.testclient import TestClient

from app.main import app


def test_health_without_database_configuration() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "INDUS AI API",
        "version": "0.1.0",
        "environment": "development",
        "database": "not_configured",
        "supabase": "not_configured",
        "storage": "not_configured",
        "pgvector": "not_configured",
    }


def test_local_frontend_cors_preflight() -> None:
    with TestClient(app) as client:
        response = client.options(
            "/documents",
            headers={
                "Origin": "http://127.0.0.1:3000",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "authorization",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:3000"


def test_public_liveness_probe() -> None:
    from app.core.auth import get_current_user

    app.dependency_overrides.pop(get_current_user, None)
    with TestClient(app) as client:
        response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "alive"}
