from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.types import enum_type
from app.models.enums import SubscriptionInterval, SubscriptionStatus, UserPlan

if TYPE_CHECKING:
    from app.models.billing_payment import BillingPayment
    from app.models.job import Job
    from app.models.refresh_token import RefreshToken
    from app.models.upload import Upload


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("credits_remaining >= 0", name="credits_remaining_non_negative"),
    )

    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    plan: Mapped[UserPlan] = mapped_column(
        enum_type(UserPlan, "user_plan"),
        nullable=False,
        default=UserPlan.FREE,
        server_default=UserPlan.FREE.value,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="1",
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
    )
    is_admin: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
    )
    credits_remaining: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=30,
        server_default="30",
    )
    last_credit_refresh: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        server_default=func.now(),
    )
    subscription_status: Mapped[SubscriptionStatus] = mapped_column(
        enum_type(SubscriptionStatus, "subscription_status"),
        nullable=False,
        default=SubscriptionStatus.INACTIVE,
        server_default=SubscriptionStatus.INACTIVE.value,
    )
    subscription_interval: Mapped[SubscriptionInterval | None] = mapped_column(
        enum_type(SubscriptionInterval, "subscription_interval"),
        nullable=True,
    )
    subscription_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    subscription_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    payments: Mapped[list["BillingPayment"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    uploads: Mapped[list["Upload"]] = relationship(back_populates="owner")
    jobs: Mapped[list["Job"]] = relationship(back_populates="owner")

    @property
    def normalized_email(self) -> str:
        return self.email.strip().lower()

    @property
    def plan_type(self) -> UserPlan:
        return self.plan
