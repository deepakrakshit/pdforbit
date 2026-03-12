from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import SubscriptionInterval, SubscriptionStatus, UserPlan


class UserProfileResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: UUID
    email: str = Field(min_length=3, max_length=320)
    plan_type: UserPlan
    is_admin: bool
    credits_remaining: int = Field(ge=0)
    credit_limit: int = Field(ge=0)
    jobs_processed: int = Field(ge=0)
    subscription_status: SubscriptionStatus
    subscription_interval: SubscriptionInterval | None = None
    subscription_started_at: datetime | None = None
    subscription_expires_at: datetime | None = None
    created_at: datetime
    last_credit_refresh: datetime