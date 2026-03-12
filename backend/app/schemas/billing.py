from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import BillingPlanCode, PaymentStatus, SubscriptionInterval, SubscriptionStatus, UserPlan


class BillingOrderRegistrationRequest(BaseModel):
    user_id: UUID
    plan_code: BillingPlanCode
    razorpay_order_id: str = Field(min_length=10, max_length=64)
    receipt: str = Field(min_length=4, max_length=128)
    amount_paise: int = Field(gt=0)
    currency: str = Field(min_length=3, max_length=8)


class BillingActivationRequest(BaseModel):
    user_id: UUID
    plan_code: BillingPlanCode
    razorpay_order_id: str = Field(min_length=10, max_length=64)
    razorpay_payment_id: str = Field(min_length=10, max_length=64)
    amount_paise: int = Field(gt=0)
    currency: str = Field(min_length=3, max_length=8)
    status: PaymentStatus
    signature_verified: bool = True
    provider_subscription_id: str | None = Field(default=None, max_length=64)
    paid_at: datetime | None = None
    raw_payload: dict[str, Any] | None = None


class BillingWebhookEventRequest(BaseModel):
    event: str = Field(min_length=3, max_length=128)
    payload: dict[str, Any]


class SubscriptionSnapshotResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    user_id: UUID
    plan_type: UserPlan
    credits_remaining: int = Field(ge=0)
    credit_limit: int = Field(ge=0)
    subscription_status: SubscriptionStatus
    subscription_interval: SubscriptionInterval | None = None
    subscription_started_at: datetime | None = None
    subscription_expires_at: datetime | None = None