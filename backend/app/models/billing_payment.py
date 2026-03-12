from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.types import enum_type
from app.models.enums import BillingPlanCode, PaymentProvider, PaymentStatus, SubscriptionInterval

if TYPE_CHECKING:
    from app.models.user import User


class BillingPayment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "billing_payments"
    __table_args__ = (
        CheckConstraint("amount_paise >= 0", name="billing_payment_amount_non_negative"),
    )

    user_id: Mapped[object] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider: Mapped[PaymentProvider] = mapped_column(
        enum_type(PaymentProvider, "payment_provider"),
        nullable=False,
        default=PaymentProvider.RAZORPAY,
        server_default=PaymentProvider.RAZORPAY.value,
    )
    plan_code: Mapped[BillingPlanCode] = mapped_column(
        enum_type(BillingPlanCode, "billing_plan_code"),
        nullable=False,
    )
    subscription_interval: Mapped[SubscriptionInterval] = mapped_column(
        enum_type(SubscriptionInterval, "billing_subscription_interval"),
        nullable=False,
    )
    status: Mapped[PaymentStatus] = mapped_column(
        enum_type(PaymentStatus, "payment_status"),
        nullable=False,
        default=PaymentStatus.CREATED,
        server_default=PaymentStatus.CREATED.value,
    )
    amount_paise: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="INR", server_default="INR")
    provider_order_id: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True, index=True)
    provider_payment_id: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True, index=True)
    provider_subscription_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    receipt: Mapped[str | None] = mapped_column(String(128), nullable=True, unique=True, index=True)
    signature_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    raw_payload: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped["User"] = relationship(back_populates="payments")