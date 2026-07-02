"""Phase 10 Supabase JWT authentication and role tests."""

import time
import uuid

import jwt
import pytest
import httpx
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient

from app.core.auth import (
    AuthenticatedUser,
    SupabaseJwtVerifier,
    TokenVerificationError,
    get_current_user,
)
from app.core.config import Settings
from app.main import app
from app.models.enums import UserRole

JWT_SECRET = "test-secret-that-is-long-enough-for-hs256-validation"
ISSUER = "https://example.supabase.co/auth/v1"


def access_token(**overrides: object) -> str:
    now = int(time.time())
    claims: dict[str, object] = {
        "sub": str(uuid.uuid4()),
        "aud": "authenticated",
        "iss": ISSUER,
        "iat": now,
        "exp": now + 300,
        "email": "operator@example.com",
    }
    claims.update(overrides)
    return jwt.encode(claims, JWT_SECRET, algorithm="HS256")


def verifier() -> SupabaseJwtVerifier:
    return SupabaseJwtVerifier(
        Settings(
            supabase_url="https://example.supabase.co",
            supabase_jwt_secret=JWT_SECRET,
            _env_file=None,
        )
    )


@pytest.mark.asyncio
async def test_legacy_supabase_token_is_verified() -> None:
    service = verifier()
    try:
        claims = await service.verify(access_token())
    finally:
        await service.close()

    assert claims["aud"] == "authenticated"
    assert claims["email"] == "operator@example.com"


@pytest.mark.asyncio
async def test_expired_token_is_rejected() -> None:
    service = verifier()
    try:
        with pytest.raises(TokenVerificationError):
            await service.verify(access_token(exp=int(time.time()) - 120))
    finally:
        await service.close()


@pytest.mark.asyncio
async def test_modern_es256_token_is_verified_from_jwks() -> None:
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_jwk = jwt.algorithms.ECAlgorithm.to_jwk(private_key.public_key(), as_dict=True)
    public_jwk.update({"kid": "test-key", "alg": "ES256", "use": "sig"})

    async def jwks_response(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/.well-known/jwks.json")
        return httpx.Response(200, json={"keys": [public_jwk]})

    service = SupabaseJwtVerifier(
        Settings(supabase_url="https://example.supabase.co", _env_file=None)
    )
    await service._http.aclose()
    service._http = httpx.AsyncClient(transport=httpx.MockTransport(jwks_response))
    now = int(time.time())
    token = jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "aud": "authenticated",
            "iss": ISSUER,
            "iat": now,
            "exp": now + 300,
        },
        private_key,
        algorithm="ES256",
        headers={"kid": "test-key"},
    )
    try:
        claims = await service.verify(token)
    finally:
        await service.close()

    assert claims["aud"] == "authenticated"


@pytest.mark.asyncio
async def test_wrong_token_audience_is_rejected() -> None:
    service = verifier()
    try:
        with pytest.raises(TokenVerificationError):
            await service.verify(access_token(aud="service_role"))
    finally:
        await service.close()


def test_api_rejects_missing_bearer_token() -> None:
    app.dependency_overrides.pop(get_current_user, None)
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_operator_cannot_access_analytics() -> None:
    operator = AuthenticatedUser(
        id=uuid.uuid4(),
        email="operator@example.com",
        role=UserRole.OPERATOR,
        department_id=None,
    )
    app.dependency_overrides[get_current_user] = lambda: operator
    with TestClient(app) as client:
        response = client.get("/analytics")

    assert response.status_code == 403


def test_operator_cannot_upload() -> None:
    operator = AuthenticatedUser(
        id=uuid.uuid4(),
        email="operator@example.com",
        role=UserRole.OPERATOR,
        department_id=None,
    )
    app.dependency_overrides[get_current_user] = lambda: operator
    with TestClient(app) as client:
        response = client.post(
            "/upload",
            files={"file": ("manual.pdf", b"%PDF-1.4 test", "application/pdf")},
        )

    assert response.status_code == 403
