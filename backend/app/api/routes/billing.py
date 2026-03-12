from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_billing_service, require_internal_api_access
from app.schemas.billing import (
    BillingActivationRequest,
    BillingOrderRegistrationRequest,
    BillingWebhookEventRequest,
    SubscriptionSnapshotResponse,
)
from app.services.billing_service import BillingService

router = APIRouter(prefix="/billing")


@router.post(
    "/internal/order-created",
    dependencies=[Depends(require_internal_api_access)],
    include_in_schema=False,
    status_code=status.HTTP_201_CREATED,
)
def register_billing_order(
    request: BillingOrderRegistrationRequest,
    billing_service: Annotated[BillingService, Depends(get_billing_service)],
) -> dict[str, str]:
    payment = billing_service.register_order(
        user_id=request.user_id,
        plan_code=request.plan_code,
        razorpay_order_id=request.razorpay_order_id,
        receipt=request.receipt,
        amount_paise=request.amount_paise,
        currency=request.currency,
    )
    return {"payment_record_id": str(payment.id), "status": payment.status.value}


@router.post(
    "/internal/activate",
    response_model=SubscriptionSnapshotResponse,
    dependencies=[Depends(require_internal_api_access)],
    include_in_schema=False,
)
def activate_billing_subscription(
    request: BillingActivationRequest,
    billing_service: Annotated[BillingService, Depends(get_billing_service)],
) -> SubscriptionSnapshotResponse:
    return billing_service.activate_subscription(
        user_id=request.user_id,
        plan_code=request.plan_code,
        razorpay_order_id=request.razorpay_order_id,
        razorpay_payment_id=request.razorpay_payment_id,
        amount_paise=request.amount_paise,
        currency=request.currency,
        status_value=request.status,
        signature_verified=request.signature_verified,
        provider_subscription_id=request.provider_subscription_id,
        paid_at=request.paid_at,
        raw_payload=request.raw_payload,
    )


@router.post(
    "/internal/webhook",
    response_model=SubscriptionSnapshotResponse | None,
    dependencies=[Depends(require_internal_api_access)],
    include_in_schema=False,
)
def process_billing_webhook(
    request: BillingWebhookEventRequest,
    billing_service: Annotated[BillingService, Depends(get_billing_service)],
) -> SubscriptionSnapshotResponse | None:
    return billing_service.handle_webhook_event(event_name=request.event, payload=request.payload)