"""Supabase access-token verification and profile-backed authorization."""

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass
from functools import lru_cache
from typing import Annotated, Any, Awaitable, Callable

import httpx
import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.core.config import Settings, get_settings
from app.database.session import Database, get_database
from app.models.enums import UserRole
from app.models.profile import Profile

bearer_scheme = HTTPBearer(auto_error=False, scheme_name="Supabase access token")
logger = logging.getLogger(__name__)


class TokenVerificationError(Exception):
    """A bearer token could not be cryptographically verified."""


@dataclass(frozen=True, slots=True)
class AuthenticatedUser:
    """Verified Supabase identity enriched with the authoritative database role."""

    id: uuid.UUID
    email: str | None
    role: UserRole
    department_id: uuid.UUID | None


class SupabaseJwtVerifier:
    """Verify modern JWKS tokens and legacy HS256 Supabase tokens."""

    ASYMMETRIC_ALGORITHMS = {"ES256", "RS256"}

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._http = httpx.AsyncClient(timeout=settings.supabase_request_timeout)
        self._jwks: dict[str, Any] | None = None
        self._jwks_expires_at = 0.0
        self._lock = asyncio.Lock()

    @property
    def issuer(self) -> str:
        if self.settings.supabase_url is None:
            raise TokenVerificationError("Supabase authentication is not configured")
        return f"{str(self.settings.supabase_url).rstrip('/')}/auth/v1"

    async def verify(self, token: str) -> dict[str, Any]:
        """Return validated claims or raise a non-sensitive verification error."""

        try:
            header = jwt.get_unverified_header(token)
            algorithm = header.get("alg")
            if algorithm == "HS256":
                if self.settings.supabase_jwt_secret is None:
                    raise TokenVerificationError(
                        "Legacy Supabase JWT secret is not configured"
                    )
                key: Any = self.settings.supabase_jwt_secret.get_secret_value()
            elif algorithm in self.ASYMMETRIC_ALGORITHMS:
                key = await self._signing_key(header.get("kid"))
            else:
                raise TokenVerificationError("Unsupported JWT signing algorithm")

            claims = jwt.decode(
                token,
                key=key,
                algorithms=[algorithm],
                audience=self.settings.supabase_jwt_audience,
                issuer=self.issuer,
                leeway=30,
                options={"require": ["sub", "aud", "exp", "iat"]},
            )
            uuid.UUID(str(claims["sub"]))
            return claims
        except TokenVerificationError:
            raise
        except (jwt.PyJWTError, ValueError, KeyError) as exc:
            raise TokenVerificationError("Invalid or expired access token") from exc

    async def _signing_key(self, key_id: str | None) -> Any:
        if not key_id:
            raise TokenVerificationError("JWT signing key identifier is missing")
        jwks = await self._get_jwks()
        key_data = next((key for key in jwks.get("keys", []) if key.get("kid") == key_id), None)
        if key_data is None:
            jwks = await self._get_jwks(force=True)
            key_data = next(
                (key for key in jwks.get("keys", []) if key.get("kid") == key_id), None
            )
        if key_data is None:
            raise TokenVerificationError("JWT signing key was not found")
        try:
            return jwt.PyJWK.from_dict(key_data).key
        except jwt.PyJWTError as exc:
            raise TokenVerificationError("JWT signing key is invalid") from exc

    async def _get_jwks(self, force: bool = False) -> dict[str, Any]:
        now = time.monotonic()
        if not force and self._jwks is not None and now < self._jwks_expires_at:
            return self._jwks
        async with self._lock:
            now = time.monotonic()
            if not force and self._jwks is not None and now < self._jwks_expires_at:
                return self._jwks
            try:
                response = await self._http.get(f"{self.issuer}/.well-known/jwks.json")
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload.get("keys"), list):
                    raise ValueError("Malformed JWKS")
            except Exception as exc:
                raise TokenVerificationError("Supabase signing keys are unavailable") from exc
            self._jwks = payload
            self._jwks_expires_at = now + self.settings.supabase_jwks_cache_seconds
            return payload

    async def close(self) -> None:
        await self._http.aclose()


@lru_cache
def get_jwt_verifier() -> SupabaseJwtVerifier:
    return SupabaseJwtVerifier(get_settings())


def unauthorized(detail: str = "Authentication required") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    verifier: Annotated[SupabaseJwtVerifier, Depends(get_jwt_verifier)],
    database: Annotated[Database, Depends(get_database)],
) -> AuthenticatedUser:
    """Authenticate a bearer token and load/create its application profile."""

    if credentials is None or credentials.scheme.lower() != "bearer":
        logger.warning(
            "Authentication credentials missing",
            extra={"event": "authentication_failed", "reason": "missing_credentials"},
        )
        raise unauthorized()
    try:
        claims = await verifier.verify(credentials.credentials)
    except TokenVerificationError as exc:
        logger.warning(
            "Access token verification failed",
            extra={"event": "authentication_failed", "reason": "invalid_token"},
        )
        raise unauthorized("Invalid or expired access token") from exc

    user_id = uuid.UUID(str(claims["sub"]))
    if database.session_factory is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is not configured",
        )
    async with database.session_factory() as session:
        profile = await session.get(Profile, user_id)
        profile_created = profile is None
        if profile is None:
            metadata = claims.get("user_metadata") or {}
            email = claims.get("email")
            display_name = metadata.get("full_name") or metadata.get("name") or email or "INDUS User"
            profile = Profile(
                id=user_id,
                full_name=str(display_name)[:160],
                role=UserRole.OPERATOR,
            )
            session.add(profile)
            await session.flush()
        user = AuthenticatedUser(
            id=profile.id,
            email=claims.get("email"),
            role=profile.role,
            department_id=profile.department_id,
        )
        await session.commit()

    logger.info(
        "User authenticated",
        extra={
            "event": "authentication_succeeded",
            "user_id": str(user.id),
            "role": user.role.value,
            "profile_created": profile_created,
        },
    )

    return user


RoleDependency = Callable[..., Awaitable[AuthenticatedUser]]


def require_roles(*allowed: UserRole) -> RoleDependency:
    """Create a dependency that authorizes only database-backed roles."""

    allowed_set = frozenset(allowed)

    async def role_guard(
        user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    ) -> AuthenticatedUser:
        if user.role not in allowed_set:
            logger.warning(
                "Role authorization denied",
                extra={
                    "event": "authorization_denied",
                    "user_id": str(user.id),
                    "role": user.role.value,
                },
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return user

    return role_guard
