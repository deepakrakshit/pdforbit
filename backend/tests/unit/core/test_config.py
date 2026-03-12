from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.config import AppSettings


def test_settings_load_default_values() -> None:
    settings = AppSettings()

    assert settings.app_name == "PdfORBIT API"
    assert settings.api_v1_prefix == "/api/v1"
    assert settings.request_id_header == "X-Request-ID"
    assert settings.database_url == "sqlite+pysqlite:///./pdforbit.db"
    assert settings.files_root.is_absolute()
    assert settings.jwt_access_secret is not None
    assert settings.jwt_refresh_secret is not None
    assert settings.download_signing_secret is not None
    assert len(settings.jwt_access_secret) >= 32
    assert len(settings.jwt_refresh_secret) >= 32
    assert len(settings.download_signing_secret) >= 32
    assert settings.retention_minutes == 60
    assert settings.guest_max_upload_mb == 50
    assert settings.user_max_upload_mb == 250
    assert settings.redis_url == "redis://localhost:6379/0"
    assert settings.queue_default_timeout_seconds == 900
    assert settings.download_url_ttl_seconds == 900


def test_settings_parse_comma_separated_lists() -> None:
    settings = AppSettings(
        CORS_ORIGINS="http://localhost:3000, https://app.pdforbit.app",
        ALLOWED_HOSTS="api.pdforbit.app,localhost",
    )

    assert settings.cors_origins == [
        "http://localhost:3000",
        "https://app.pdforbit.app",
    ]
    assert settings.allowed_hosts == ["api.pdforbit.app", "localhost"]


def test_api_prefix_must_start_with_slash() -> None:
    with pytest.raises(ValidationError):
        AppSettings(API_V1_PREFIX="api/v1")


def test_api_prefix_must_not_end_with_slash() -> None:
    with pytest.raises(ValidationError):
        AppSettings(API_V1_PREFIX="/api/v1/")


def test_database_url_defaults_for_test_environment() -> None:
    settings = AppSettings(APP_ENV="test")

    assert settings.database_url == "sqlite+pysqlite:///:memory:"


def test_database_url_is_required_in_production() -> None:
    with pytest.raises(ValidationError):
        AppSettings(APP_ENV="production")


def test_jwt_secrets_are_required_in_production() -> None:
    with pytest.raises(ValidationError):
        AppSettings(
            APP_ENV="production",
            DATABASE_URL="postgresql+psycopg://user:password@localhost:5432/pdforbit",
        )


def test_jwt_secrets_must_be_at_least_32_characters() -> None:
    with pytest.raises(ValidationError):
        AppSettings(
            APP_ENV="test",
            JWT_ACCESS_SECRET="short-secret",
            JWT_REFRESH_SECRET="another-short-secret",
        )


def test_download_url_ttl_must_not_exceed_retention_window() -> None:
    with pytest.raises(ValidationError):
        AppSettings(
            APP_ENV="test",
            RETENTION_MINUTES=10,
            DOWNLOAD_URL_TTL_SECONDS=3600,
        )


def test_user_upload_limit_must_be_greater_than_guest_limit() -> None:
    with pytest.raises(ValidationError):
        AppSettings(
            APP_ENV="test",
            GUEST_MAX_UPLOAD_MB=100,
            USER_MAX_UPLOAD_MB=50,
        )


def test_redis_url_is_required_in_production() -> None:
    with pytest.raises(ValidationError):
        AppSettings(
            APP_ENV="production",
            DATABASE_URL="postgresql+psycopg://user:password@localhost:5432/pdforbit",
            JWT_ACCESS_SECRET="production-access-secret-with-32-plus-chars",
            JWT_REFRESH_SECRET="production-refresh-secret-with-32-plus-chars",
        )
