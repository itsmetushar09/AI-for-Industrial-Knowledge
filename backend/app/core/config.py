"""Typed configuration loaded exclusively from environment variables."""

from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, AnyHttpUrl, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError


class Settings(BaseSettings):
    """Runtime settings for the INDUS AI API."""

    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )

    app_name: str = "INDUS AI API"
    app_version: str = "0.1.0"
    app_env: str = "development"
    debug: bool = False
    log_level: str = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = Field(default=8000, ge=1, le=65535)
    cors_origins: str = "http://127.0.0.1:3000,http://localhost:3000,http://127.0.0.1:5173,http://localhost:5173"

    database_url: SecretStr | None = None
    database_pool_size: int = Field(default=5, ge=1)
    database_max_overflow: int = Field(default=10, ge=0)
    database_pool_timeout: int = Field(default=30, ge=1)

    supabase_url: AnyHttpUrl | None = None
    supabase_publishable_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("SUPABASE_PUBLISHABLE_KEY", "SUPABASE_ANON_KEY"),
    )
    supabase_secret_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("SUPABASE_SECRET_KEY", "SUPABASE_SERVICE_ROLE_KEY"),
    )
    supabase_request_timeout: int = Field(default=20, ge=1, le=120)
    supabase_storage_bucket: str = Field(default="documents", min_length=1)
    supabase_storage_max_file_size: int = Field(default=52_428_800, ge=1)
    supabase_jwt_secret: SecretStr | None = None
    supabase_jwt_audience: str = "authenticated"
    supabase_jwks_cache_seconds: int = Field(default=600, ge=60, le=86400)

    openai_api_key: SecretStr | None = None
    gemini_api_key: SecretStr | None = None
    ai_provider: Literal["openai", "gemini"] = "gemini"
    openai_embedding_model: str = "text-embedding-3-small"
    openai_embedding_dimensions: int = Field(default=1536, ge=1)
    openai_embedding_batch_size: int = Field(default=64, ge=1, le=2048)
    openai_chat_model: str = "gpt-5.4-mini"
    openai_chat_max_output_tokens: int = Field(default=1200, ge=100, le=8192)
    gemini_embedding_model: str = "gemini-embedding-001"
    gemini_chat_model: str = "gemini-2.5-flash-lite"
    gemini_embedding_batch_size: int = Field(default=64, ge=1, le=100)
    openai_request_timeout: int = Field(default=60, ge=1, le=300)
    rag_top_k: int = Field(default=5, ge=1, le=20)
    document_chunk_tokens: int = Field(default=800, ge=100, le=8192)
    document_chunk_overlap: int = Field(default=150, ge=0)

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, value: str) -> str:
        """Normalize and validate standard Python logging levels."""

        normalized = value.upper()
        allowed = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}
        if normalized not in allowed:
            raise ValueError(f"LOG_LEVEL must be one of: {', '.join(sorted(allowed))}")
        return normalized

    @field_validator(
        "database_url",
        "supabase_url",
        "supabase_publishable_key",
        "supabase_secret_key",
        "supabase_jwt_secret",
        "openai_api_key",
        "gemini_api_key",
        mode="before",
    )
    @classmethod
    def empty_string_is_unset(cls, value: object) -> object:
        """Allow the checked-in environment template to contain blank values."""

        return None if value == "" else value

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: SecretStr | None) -> SecretStr | None:
        """Reject accidental use of the HTTPS Supabase project API URL."""

        if value is None:
            return None
        url = value.get_secret_value()
        allowed_schemes = ("postgresql://", "postgres://", "postgresql+asyncpg://")
        if not url.startswith(allowed_schemes):
            raise ValueError(
                "DATABASE_URL must be a PostgreSQL connection string beginning with "
                "postgresql://; do not use the https:// Supabase project URL"
            )
        try:
            parsed = make_url(url)
        except ArgumentError as exc:
            raise ValueError("DATABASE_URL is not a valid PostgreSQL URI") from exc
        if parsed.host is None:
            raise ValueError("DATABASE_URL must contain a PostgreSQL hostname")
        if "@" in parsed.host:
            raise ValueError(
                "DATABASE_URL contains an unescaped @ in its password; percent-encode "
                "special password characters (for example, replace @ with %40)"
            )
        return value

    @model_validator(mode="after")
    def validate_rag_configuration(self) -> "Settings":
        """Keep token windows and deployed vector dimensions compatible."""

        if self.document_chunk_overlap >= self.document_chunk_tokens:
            raise ValueError("DOCUMENT_CHUNK_OVERLAP must be smaller than DOCUMENT_CHUNK_TOKENS")
        if self.openai_embedding_dimensions != 1536:
            raise ValueError("OPENAI_EMBEDDING_DIMENSIONS must remain 1536 for the deployed schema")
        return self

    @property
    def ai_configured(self) -> bool:
        """Return whether the selected AI provider has a server-side key."""

        if self.ai_provider == "gemini":
            return self.gemini_api_key is not None
        return self.openai_api_key is not None

    @property
    def active_embedding_model(self) -> str:
        """Return the model associated with the selected embedding space."""

        if self.ai_provider == "gemini":
            return self.gemini_embedding_model
        return self.openai_embedding_model

    @property
    def supabase_public_configured(self) -> bool:
        """Return whether public Auth/PostgREST access can be initialized."""

        return self.supabase_url is not None and self.supabase_publishable_key is not None

    @property
    def supabase_admin_configured(self) -> bool:
        """Return whether privileged server-side access can be initialized."""

        return self.supabase_url is not None and self.supabase_secret_key is not None

    @property
    def allowed_cors_origins(self) -> list[str]:
        """Return normalized browser origins from the comma-separated environment value."""

        return [origin.strip().rstrip("/") for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return one immutable-in-practice settings object per process."""

    return Settings()
