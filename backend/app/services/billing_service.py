from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db.repositories.billing_payment import BillingPaymentRepository
from app.db.repositories.user import UserRepository
from app.models.billing_payment import BillingPayment
from app.models.enums import BillingPlanCode, PaymentStatus, SubscriptionInterval, SubscriptionStatus, UserPlan
from app.models.user import User
from app.schemas.billing import SubscriptionSnapshotResponse
from app.services.credit_service import CreditService


@dataclass(frozen=True)
class PlanSpec:
    code: BillingPlanCode
    interval: SubscriptionInterval
    amount_paise: int
    duration: timedelta


class BillingService:
    PLAN_SPECS: dict[BillingPlanCode, PlanSpec] = {
        BillingPlanCode.PRO_MONTHLY: PlanSpec(
            code=BillingPlanCode.PRO_MONTHLY,
            interval=SubscriptionInterval.MONTHLY,
            amount_paise=50_000,
            duration=timedelta(days=30),
        ),
        BillingPlanCode.PRO_YEARLY: PlanSpec(
            code=BillingPlanCode.PRO_YEARLY,
            interval=SubscriptionInterval.YEARLY,
            amount_paise=240_000,
            duration=timedelta(days=365),
        ),
    }

    def __init__(self, *, session: Session) -> None:
        self._session = session
        self._users = UserRepository(session)
        self._payments = BillingPaymentRepository(session)
        self._credits = CreditService()

    def register_order(
        self,
        *,
        user_id: UUID,
        plan_code: BillingPlanCode,
        razorpay_order_id: str,
        receipt: str,
        amount_paise: int,
        currency: str,
    ) -> BillingPayment:
        user = self._get_user(user_id)
        spec = self.get_plan_spec(plan_code)
        self._validate_amount(plan_code=plan_code, amount_paise=amount_paise, currency=currency)

        payment = self._payments.get_by_provider_order_id(razorpay_order_id)
        if payment is None:
            payment = BillingPayment(
                user_id=user.id,
                plan_code=plan_code,
                subscription_interval=spec.interval,
                status=PaymentStatus.CREATED,
                amount_paise=amount_paise,
                currency=currency.upper(),
                provider_order_id=razorpay_order_id,
                receipt=receipt,
            )
        else:
            payment.user_id = user.id
            payment.plan_code = plan_code
            payment.subscription_interval = spec.interval
            payment.amount_paise = amount_paise
            payment.currency = currency.upper()
            payment.receipt = receipt

        self._payments.add(payment)
        self._session.flush()
        return payment

    def activate_subscription(
        self,
        *,
        user_id: UUID,
        plan_code: BillingPlanCode,
        razorpay_order_id: str,
        razorpay_payment_id: str,
        amount_paise: int,
        currency: str,
        status_value: PaymentStatus,
        signature_verified: bool,
        provider_subscription_id: str | None = None,
        paid_at: datetime | None = None,
        raw_payload: dict[str, Any] | None = None,
    ) -> SubscriptionSnapshotResponse:
        if status_value not in {PaymentStatus.AUTHORIZED, PaymentStatus.CAPTURED}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payment is not in a capturable state.",
            )

        user = self._get_user(user_id)
        spec = self.get_plan_spec(plan_code)
        self._validate_amount(plan_code=plan_code, amount_paise=amount_paise, currency=currency)

        payment = self._payments.get_by_provider_payment_id(razorpay_payment_id)
        if payment is None:
            payment = self._payments.get_by_provider_order_id(razorpay_order_id)

        if payment is None:
            payment = BillingPayment(
                user_id=user.id,
                plan_code=plan_code,
                subscription_interval=spec.interval,
                amount_paise=amount_paise,
                currency=currency.upper(),
                provider_order_id=razorpay_order_id,
            )

        current_time = self._normalize_datetime(paid_at or datetime.now(timezone.utc))
        payment.user_id = user.id
        payment.plan_code = plan_code
        payment.subscription_interval = spec.interval
        payment.amount_paise = amount_paise
        payment.currency = currency.upper()
        payment.provider_order_id = razorpay_order_id
        payment.provider_payment_id = razorpay_payment_id
        payment.provider_subscription_id = provider_subscription_id
        payment.status = status_value
        payment.signature_verified = signature_verified
        payment.paid_at = current_time
        payment.raw_payload = json.dumps(raw_payload) if raw_payload is not None else payment.raw_payload

        next_period_start = current_time
        if user.subscription_status == SubscriptionStatus.ACTIVE and user.subscription_expires_at is not None:
            existing_expiry = self._normalize_datetime(user.subscription_expires_at)
            if existing_expiry > current_time:
                next_period_start = existing_expiry

        next_expiry = next_period_start + spec.duration
        payment.expires_at = next_expiry

        user.plan = UserPlan.PRO
        user.subscription_status = SubscriptionStatus.ACTIVE
        user.subscription_interval = spec.interval
        user.subscription_started_at = current_time
        user.subscription_expires_at = next_expiry
        user.credits_remaining = self._credits.PRO_DAILY_CREDITS
        user.last_credit_refresh = current_time

        self._payments.add(payment)
        self._session.add(user)
        self._session.flush()
        return self._build_snapshot(user)

    def handle_webhook_event(self, *, event_name: str, payload: dict[str, Any]) -> SubscriptionSnapshotResponse | None:
        if event_name == "payment.captured":
            payment_entity = self._nested_entity(payload, "payment")
            order_id = self._read_string(payment_entity, "order_id")
            payment_id = self._read_string(payment_entity, "id")
            notes = self._read_notes(payment_entity)
            plan_code = self._resolve_plan_code(notes, order_id)
            user_id = self._resolve_user_id(notes, order_id)
            return self.activate_subscription(
                user_id=user_id,
                plan_code=plan_code,
                razorpay_order_id=order_id,
                razorpay_payment_id=payment_id,
                amount_paise=self._read_int(payment_entity, "amount"),
                currency=self._read_string(payment_entity, "currency"),
                status_value=PaymentStatus.CAPTURED,
                signature_verified=True,
                paid_at=self._read_unix_timestamp(payment_entity, "captured_at"),
                raw_payload=payload,
            )

        if event_name == "subscription.charged":
            subscription_entity = self._nested_entity(payload, "subscription")
            payment_entity = self._nested_optional_entity(payload, "payment")
            notes = self._read_notes(subscription_entity)
            order_id = self._read_string(payment_entity or {}, "order_id")
            payment_id = self._read_string(payment_entity or {}, "id")
            provider_subscription_id = self._read_string(subscription_entity, "id")
            plan_code = self._resolve_plan_code(notes, order_id, provider_subscription_id)
            user_id = self._resolve_user_id(notes, order_id, provider_subscription_id)
            return self.activate_subscription(
                user_id=user_id,
                plan_code=plan_code,
                razorpay_order_id=order_id or f"subscription:{provider_subscription_id}",
                razorpay_payment_id=payment_id or provider_subscription_id,
                amount_paise=self._read_int(payment_entity or subscription_entity, "amount"),
                currency=self._read_string(payment_entity or subscription_entity, "currency"),
                status_value=PaymentStatus.CAPTURED,
                signature_verified=True,
                provider_subscription_id=provider_subscription_id,
                paid_at=self._read_unix_timestamp(subscription_entity, "current_start") or datetime.now(timezone.utc),
                raw_payload=payload,
            )

        if event_name == "subscription.cancelled":
            subscription_entity = self._nested_entity(payload, "subscription")
            notes = self._read_notes(subscription_entity)
            provider_subscription_id = self._read_string(subscription_entity, "id")
            user_id = self._resolve_user_id(notes, provider_subscription_id=provider_subscription_id)
            return self.cancel_subscription(
                user_id=user_id,
                provider_subscription_id=provider_subscription_id,
                raw_payload=payload,
            )

        return None

    def cancel_subscription(
        self,
        *,
        user_id: UUID,
        provider_subscription_id: str | None = None,
        raw_payload: dict[str, Any] | None = None,
    ) -> SubscriptionSnapshotResponse:
        user = self._get_user(user_id)
        current_time = datetime.now(timezone.utc)

        if provider_subscription_id:
            payment = self._payments.get_latest_by_provider_subscription_id(provider_subscription_id)
            if payment is not None:
                payment.status = PaymentStatus.CANCELLED
                payment.raw_payload = json.dumps(raw_payload) if raw_payload is not None else payment.raw_payload
                self._payments.add(payment)

        user.plan = UserPlan.FREE
        user.subscription_status = SubscriptionStatus.CANCELLED
        user.subscription_interval = None
        user.subscription_started_at = None
        user.subscription_expires_at = current_time
        user.credits_remaining = min(user.credits_remaining, self._credits.FREE_DAILY_CREDITS)
        user.last_credit_refresh = current_time
        self._session.add(user)
        self._session.flush()
        return self._build_snapshot(user)

    @classmethod
    def get_plan_spec(cls, plan_code: BillingPlanCode) -> PlanSpec:
        spec = cls.PLAN_SPECS.get(plan_code)
        if spec is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported billing plan.")
        return spec

    def _build_snapshot(self, user: User) -> SubscriptionSnapshotResponse:
        return SubscriptionSnapshotResponse(
            user_id=user.id,
            plan_type=user.plan_type,
            credits_remaining=user.credits_remaining,
            credit_limit=self._credits.get_user_credit_limit(user),
            subscription_status=user.subscription_status,
            subscription_interval=user.subscription_interval,
            subscription_started_at=user.subscription_started_at,
            subscription_expires_at=user.subscription_expires_at,
        )

    def _get_user(self, user_id: UUID) -> User:
        user = self._users.get(user_id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
        return user

    def _validate_amount(self, *, plan_code: BillingPlanCode, amount_paise: int, currency: str) -> None:
        spec = self.get_plan_spec(plan_code)
        if amount_paise != spec.amount_paise or currency.upper() != "INR":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payment amount validation failed.")

    @staticmethod
    def _normalize_datetime(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @staticmethod
    def _nested_entity(payload: dict[str, Any], entity_name: str) -> dict[str, Any]:
        try:
            entity = payload["payload"][entity_name]["entity"]
        except KeyError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Missing webhook entity: {entity_name}.") from exc
        if not isinstance(entity, dict):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid webhook entity: {entity_name}.")
        return entity

    @classmethod
    def _nested_optional_entity(cls, payload: dict[str, Any], entity_name: str) -> dict[str, Any] | None:
        try:
            return cls._nested_entity(payload, entity_name)
        except HTTPException:
            return None

    @staticmethod
    def _read_notes(entity: dict[str, Any]) -> dict[str, Any]:
        notes = entity.get("notes")
        return notes if isinstance(notes, dict) else {}

    @staticmethod
    def _read_string(entity: dict[str, Any], key: str) -> str:
        value = entity.get(key)
        return value.strip() if isinstance(value, str) else ""

    @staticmethod
    def _read_int(entity: dict[str, Any], key: str) -> int:
        value = entity.get(key)
        if isinstance(value, bool) or not isinstance(value, int):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid integer field: {key}.")
        return value

    @staticmethod
    def _read_unix_timestamp(entity: dict[str, Any], key: str) -> datetime | None:
        value = entity.get(key)
        if not isinstance(value, int) or value <= 0:
            return None
        return datetime.fromtimestamp(value, tz=timezone.utc)

    def _resolve_plan_code(
        self,
        notes: dict[str, Any],
        provider_order_id: str | None = None,
        provider_subscription_id: str | None = None,
    ) -> BillingPlanCode:
        raw = notes.get("plan_code")
        if isinstance(raw, str):
            try:
                return BillingPlanCode(raw)
            except ValueError:
                pass

        payment = None
        if provider_order_id:
            payment = self._payments.get_by_provider_order_id(provider_order_id)
        if payment is None and provider_subscription_id:
            payment = self._payments.get_latest_by_provider_subscription_id(provider_subscription_id)
        if payment is not None:
            return payment.plan_code

        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unable to resolve billing plan.")

    def _resolve_user_id(
        self,
        notes: dict[str, Any],
        provider_order_id: str | None = None,
        provider_subscription_id: str | None = None,
    ) -> UUID:
        raw_user_id = notes.get("user_id")
        if isinstance(raw_user_id, str):
            try:
                return UUID(raw_user_id)
            except ValueError:
                pass

        payment = None
        if provider_order_id:
            payment = self._payments.get_by_provider_order_id(provider_order_id)
        if payment is None and provider_subscription_id:
            payment = self._payments.get_latest_by_provider_subscription_id(provider_subscription_id)
        if payment is not None:
            return payment.user_id

        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unable to resolve billing user.")