"""Configuration behavior tests."""

import pytest
from pydantic import SecretStr, ValidationError

from app.core.config import Settings
from app.database.session import normalize_database_url


def test_settings_normalize_log_level() -> None:
    settings = Settings(log_level="debug", _env_file=None)
    assert settings.log_level == "DEBUG"


def test_settings_reject_invalid_port() -> None:
    with pytest.raises(ValidationError):
        Settings(api_port=70000, _env_file=None)


def test_settings_reject_supabase_https_url_as_database_url() -> None:
    with pytest.raises(ValidationError, match="PostgreSQL connection string"):
        Settings(database_url="https://project-ref.supabase.co", _env_file=None)


def test_settings_reject_unescaped_at_in_database_password() -> None:
    malformed = (
        "postgresql://postgres.project-ref:password@with-at"
        "@aws-1-ap-southeast-1.pooler.supabase.com:5432/postgres"
    )
    with pytest.raises(ValidationError, match="unescaped @"):
        Settings(database_url=malformed, _env_file=None)


def test_postgres_url_uses_async_driver() -> None:
    assert (
        normalize_database_url("postgresql://user:pass@db.example/indus")
        == "postgresql+asyncpg://user:pass@db.example/indus"
    )


def test_blank_optional_connections_are_unset() -> None:
    settings = Settings(
        database_url="",
        supabase_url="",
        supabase_publishable_key="",
        supabase_secret_key="",
        _env_file=None,
    )
    assert settings.database_url is None
    assert settings.supabase_url is None
    assert settings.supabase_publishable_key is None
    assert settings.supabase_secret_key is None


def test_current_supabase_keys_are_supported() -> None:
    settings = Settings(
        supabase_url="https://project-ref.supabase.co",
        supabase_publishable_key=SecretStr("sb_publishable_test"),
        supabase_secret_key=SecretStr("sb_secret_test"),
        _env_file=None,
    )
    assert settings.supabase_public_configured
    assert settings.supabase_admin_configured


def test_legacy_supabase_key_aliases_are_supported() -> None:
    settings = Settings.model_validate(
        {
            "SUPABASE_URL": "https://project-ref.supabase.co",
            "SUPABASE_ANON_KEY": "legacy-anon",
            "SUPABASE_SERVICE_ROLE_KEY": "legacy-service-role",
            "_env_file": None,
        }
    )
    assert settings.supabase_publishable_key is not None
    assert settings.supabase_secret_key is not None
