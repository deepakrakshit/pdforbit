from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = Field(default="PdfORBIT API", alias="APP_NAME")
    app_env: Literal["local", "development", "test", "staging", "production"] = Field(
        default="development",
        alias="APP_ENV",
    )
    app_version: str = Field(default="0.1.0", alias="APP_VERSION")
    api_v1_prefix: str = Field(default="/api/v1", alias="API_V1_PREFIX")
    docs_enabled: bool = Field(default=True, alias="DOCS_ENABLED")
    log_format: Literal["console", "json"] = Field(default="json", alias="LOG_FORMAT")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        alias="LOG_LEVEL",
    )
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, ge=1, le=65535, alias="PORT")
    request_id_header: str = Field(default="X-Request-ID", alias="REQUEST_ID_HEADER")
    cors_origins: Annotated[list[str], NoDecode] = Field(default_factory=list, alias="CORS_ORIGINS")
    allowed_hosts: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["*"],
        alias="ALLOWED_HOSTS",
    )
    build_sha: str | None = Field(default=None, alias="BUILD_SHA")
    commit_ref: str | None = Field(default=None, alias="COMMIT_REF")
    sentry_dsn: str | None = Field(default=None, alias="SENTRY_DSN")
    database_url: str | None = Field(default=None, alias="DATABASE_URL")
    database_echo: bool = Field(default=False, alias="DATABASE_ECHO")
    files_root: Path = Field(default=Path("./var/pdforbit"), alias="FILES_ROOT")
    jwt_access_secret: str | None = Field(default=None, alias="JWT_ACCESS_SECRET")
    jwt_refresh_secret: str | None = Field(default=None, alias="JWT_REFRESH_SECRET")
    download_signing_secret: str | None = Field(default=None, alias="DOWNLOAD_SIGNING_SECRET")
    jwt_access_ttl_minutes: int = Field(default=15, ge=1, le=1440, alias="JWT_ACCESS_TTL_MINUTES")
    jwt_refresh_ttl_days: int = Field(default=30, ge=1, le=365, alias="JWT_REFRESH_TTL_DAYS")
    download_url_ttl_seconds: int = Field(default=900, ge=60, le=86400, alias="DOWNLOAD_URL_TTL_SECONDS")
    password_min_length: int = Field(default=8, ge=8, le=128, alias="PASSWORD_MIN_LENGTH")
    retention_minutes: int = Field(default=60, ge=5, le=10080, alias="RETENTION_MINUTES")
    guest_max_upload_mb: int = Field(default=50, ge=1, le=1024, alias="GUEST_MAX_UPLOAD_MB")
    user_max_upload_mb: int = Field(default=250, ge=1, le=10240, alias="USER_MAX_UPLOAD_MB")
    upload_chunk_size_bytes: int = Field(
        default=1024 * 1024,
        ge=64 * 1024,
        le=8 * 1024 * 1024,
        alias="UPLOAD_CHUNK_SIZE_BYTES",
    )
    queue_default_timeout_seconds: int = Field(
        default=900,
        ge=30,
        le=86400,
        alias="QUEUE_DEFAULT_TIMEOUT_SECONDS",
    )
    cleanup_interval_seconds: int = Field(
        default=300,
        ge=30,
        le=86400,
        alias="CLEANUP_INTERVAL_SECONDS",
    )
    stale_job_threshold_seconds: int = Field(
        default=1800,
        ge=60,
        le=7 * 24 * 60 * 60,
        alias="STALE_JOB_THRESHOLD_SECONDS",
    )
    rate_limit_uploads_per_hour: int = Field(
        default=60,
        ge=0,
        le=100000,
        alias="RATE_LIMIT_UPLOADS_PER_HOUR",
    )
    rate_limit_jobs_per_hour: int = Field(
        default=120,
        ge=0,
        le=100000,
        alias="RATE_LIMIT_JOBS_PER_HOUR",
    )
    rate_limit_auth_attempts_per_hour: int = Field(
        default=30,
        ge=0,
        le=100000,
        alias="RATE_LIMIT_AUTH_ATTEMPTS_PER_HOUR",
    )
    rate_limit_authenticated_multiplier: int = Field(
        default=4,
        ge=1,
        le=100,
        alias="RATE_LIMIT_AUTHENTICATED_MULTIPLIER",
    )
    redis_url: str | None = Field(default=None, alias="REDIS_URL")
    tesseract_bin: str = Field(default="tesseract", alias="TESSERACT_BIN")
    ocr_timeout_seconds: int = Field(default=300, ge=30, le=3600, alias="OCR_TIMEOUT_SECONDS")
    pdf_render_dpi: int = Field(default=150, ge=72, le=600, alias="PDF_RENDER_DPI")
    translation_provider: str = Field(default="disabled", alias="TRANSLATION_PROVIDER")
    translation_api_key: str | None = Field(default=None, alias="TRANSLATION_API_KEY")
    groq_api_key: str | None = Field(default=None, alias="GROQ_API_KEY")
    groq_api_base: str = Field(default="https://api.groq.com/openai/v1", alias="GROQ_API_BASE")
    groq_translate_model: str = Field(default="llama-3.3-70b-versatile", alias="GROQ_TRANSLATE_MODEL")
    groq_summary_model: str = Field(default="llama-3.1-8b-instant", alias="GROQ_SUMMARY_MODEL")
    groq_timeout_seconds: int = Field(default=120, ge=10, le=900, alias="GROQ_TIMEOUT_SECONDS")
    intelligence_chunk_chars: int = Field(default=6000, ge=500, le=32000, alias="INTELLIGENCE_CHUNK_CHARS")
    intelligence_summary_chunk_chars: int = Field(
        default=10000,
        ge=1000,
        le=48000,
        alias="INTELLIGENCE_SUMMARY_CHUNK_CHARS",
    )
    intelligence_ocr_dpi: int = Field(default=300, ge=150, le=600, alias="INTELLIGENCE_OCR_DPI")
    internal_admin_enabled: bool = Field(default=False, alias="INTERNAL_ADMIN_ENABLED")
    internal_admin_email: str | None = Field(default=None, alias="INTERNAL_ADMIN_EMAIL")
    internal_admin_password: str | None = Field(default=None, alias="INTERNAL_ADMIN_PASSWORD")
    billing_internal_api_secret: str | None = Field(default=None, alias="BILLING_INTERNAL_API_SECRET")

    @field_validator("api_v1_prefix")
    @classmethod
    def validate_api_prefix(cls, value: str) -> str:
        if not value.startswith("/"):
            raise ValueError("API_V1_PREFIX must start with '/'.")
        if value != "/" and value.endswith("/"):
            raise ValueError("API_V1_PREFIX must not end with '/'.")
        return value

    @field_validator("request_id_header")
    @classmethod
    def validate_request_id_header(cls, value: str) -> str:
        if not value:
            raise ValueError("REQUEST_ID_HEADER cannot be empty.")
        return value

    @field_validator("files_root", mode="before")
    @classmethod
    def normalize_files_root(cls, value: str | Path) -> Path:
        return Path(value).expanduser().resolve()

    @field_validator("cors_origins", "allowed_hosts", mode="before")
    @classmethod
    def parse_comma_separated_values(cls, value: str | list[str] | None) -> list[str]:
        if value in (None, "", []):
            return []
        if isinstance(value, list):
            return [item.strip() for item in value if item and item.strip()]
        normalized = value.strip()
        if normalized.startswith("["):
            try:
                parsed = json.loads(normalized)
            except json.JSONDecodeError:
                parsed = None
            if isinstance(parsed, list):
                return [str(item).strip() for item in parsed if str(item).strip()]
        return [item.strip() for item in value.split(",") if item.strip()]

    @model_validator(mode="after")
    def resolve_database_url(self) -> "AppSettings":
        if self.database_url:
            return self

        if self.app_env == "test":
            self.database_url = "sqlite+pysqlite:///:memory:"
            return self

        if self.app_env in {"local", "development"}:
            self.database_url = "sqlite+pysqlite:///./pdforbit.db"
            return self

        raise ValueError("DATABASE_URL is required in staging and production.")

    @model_validator(mode="after")
    def resolve_jwt_secrets(self) -> "AppSettings":
        if not self.jwt_access_secret or not self.jwt_refresh_secret:
            if self.app_env in {"local", "development", "test"}:
                self.jwt_access_secret = (
                    self.jwt_access_secret or "dev-access-secret-change-me-32-chars"
                )
                self.jwt_refresh_secret = (
                    self.jwt_refresh_secret or "dev-refresh-secret-change-me-32-chars"
                )
            else:
                raise ValueError(
                    "JWT_ACCESS_SECRET and JWT_REFRESH_SECRET are required outside local/test environments."
                )

        if len(self.jwt_access_secret) < 32 or len(self.jwt_refresh_secret) < 32:
            raise ValueError("JWT_ACCESS_SECRET and JWT_REFRESH_SECRET must be at least 32 characters long.")

        return self

    @model_validator(mode="after")
    def resolve_download_signing_secret(self) -> "AppSettings":
        self.download_signing_secret = self.download_signing_secret or self.jwt_access_secret
        if not self.download_signing_secret or len(self.download_signing_secret) < 32:
            raise ValueError("DOWNLOAD_SIGNING_SECRET must be at least 32 characters long.")
        return self

    @model_validator(mode="after")
    def validate_upload_limits(self) -> "AppSettings":
        if self.user_max_upload_mb < self.guest_max_upload_mb:
            raise ValueError("USER_MAX_UPLOAD_MB must be greater than or equal to GUEST_MAX_UPLOAD_MB.")
        return self

    @model_validator(mode="after")
    def validate_download_ttl(self) -> "AppSettings":
        if self.download_url_ttl_seconds > self.retention_minutes * 60:
            raise ValueError("DOWNLOAD_URL_TTL_SECONDS must not exceed RETENTION_MINUTES.")
        return self

    @model_validator(mode="after")
    def validate_internal_admin_settings(self) -> "AppSettings":
        if not self.internal_admin_enabled:
            return self

        if not self.internal_admin_email or not self.internal_admin_password:
            raise ValueError(
                "INTERNAL_ADMIN_EMAIL and INTERNAL_ADMIN_PASSWORD are required when INTERNAL_ADMIN_ENABLED is true."
            )

        if len(self.internal_admin_password) < self.password_min_length:
            raise ValueError(
                "INTERNAL_ADMIN_PASSWORD must satisfy PASSWORD_MIN_LENGTH."
            )

        return self

    @model_validator(mode="after")
    def validate_translation_provider_settings(self) -> "AppSettings":
        self.translation_api_key = self.translation_api_key or self.groq_api_key

        provider = self.translation_provider.strip().lower()
        if provider in {"", "disabled", "none"} and self.translation_api_key:
            self.translation_provider = "groq"
            provider = "groq"

        if provider != "groq":
            return self

        if not self.groq_api_base.startswith("http://") and not self.groq_api_base.startswith("https://"):
            raise ValueError("GROQ_API_BASE must be an absolute HTTP(S) URL.")

        return self

    @model_validator(mode="after")
    def validate_stale_job_threshold(self) -> "AppSettings":
        if self.stale_job_threshold_seconds < self.queue_default_timeout_seconds:
            raise ValueError("STALE_JOB_THRESHOLD_SECONDS must be greater than or equal to QUEUE_DEFAULT_TIMEOUT_SECONDS.")
        return self

    @model_validator(mode="after")
    def resolve_redis_url(self) -> "AppSettings":
        if self.redis_url:
            return self

        if self.app_env in {"local", "development"}:
            self.redis_url = "redis://localhost:6379/0"
            return self

        if self.app_env == "test":
            return self

        raise ValueError("REDIS_URL is required in staging and production.")

        return self


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    return build_settings()


def build_settings(*, env_file: str | Path | None = ".env", **overrides: Any) -> AppSettings:
    resolved_env_file: str | Path | None = env_file
    if resolved_env_file is not None:
        candidate = Path(resolved_env_file)
        resolved_env_file = candidate if candidate.exists() else None
    return AppSettings(_env_file=resolved_env_file, _env_file_encoding="utf-8", **overrides)


def clear_settings_cache() -> None:
    get_settings.cache_clear()
