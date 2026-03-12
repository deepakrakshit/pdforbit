from __future__ import annotations

from datetime import datetime
from uuid import UUID

from email_validator import EmailNotValidError, validate_email
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import SubscriptionInterval, SubscriptionStatus, UserPlan


def normalize_email_address(value: str) -> str:
    candidate = value.strip()
    try:
        validated = validate_email(
            candidate,
            check_deliverability=False,
            test_environment=True,
        )
    except EmailNotValidError as exc:
        raise ValueError(str(exc)) from exc
    return validated.normalized.lower()


class RegisterRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return normalize_email_address(value)


class LoginRequest(RegisterRequest):
    pass


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(min_length=20)


class LogoutRequest(RefreshTokenRequest):
    pass


class AuthenticatedUser(BaseModel):
    model_config = ConfigDict(from_attributes=True, frozen=True)

    id: UUID
    email: str = Field(min_length=3, max_length=320)
    plan: UserPlan
    plan_type: UserPlan
    credits_remaining: int = Field(ge=0)
    last_credit_refresh: datetime
    subscription_status: SubscriptionStatus
    subscription_interval: SubscriptionInterval | None = None
    subscription_started_at: datetime | None = None
    subscription_expires_at: datetime | None = None
    is_active: bool
    is_verified: bool
    is_admin: bool
    created_at: datetime
    updated_at: datetime

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return normalize_email_address(value)


class TokenPairResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    token_type: str = "bearer"
    access_token: str
    refresh_token: str
    access_token_expires_at: datetime
    refresh_token_expires_at: datetime
    user: AuthenticatedUser
